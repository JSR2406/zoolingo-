"""
Pet Care Expert Engine — rule-based triage + advice knowledge base.

Deterministic, offline, always-available guidance for pet caregivers:

- Emergency triage (red-flag symptoms → see a vet now)
- Vaccination due-date analysis per pet
- Feeding & weight guidance (daily calorie estimate, hydration, portion)
- Care-task advice per category (feeding/exercise/grooming/medication)
- Species-aware tips (dog / cat / bird / other)

Optionally enriched by the Sarvam LLM translator service when a question
doesn't match a known rule — the rule engine is the safe default.
"""
from __future__ import annotations

import datetime as dt
import logging
import re

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Input normalisation
# --------------------------------------------------------------------------
# The FastAPI router hands us plain dicts (or sqlite3.Row objects) for pets,
# schedules, vaccinations, records, etc., while the code below reads fields
# via attribute access (pet.species, v.next_due_on, ...).  `_rowify` wraps any
# mapping-shaped input in an attribute-access shim so expert_engine accepts
# BOTH dicts and attribute-style objects.  It is idempotent and recurses into
# lists/dicts, so it is safe to apply at every public entry point.


class _AttrRow:
    """Mapping wrapper exposing values as attributes (row.species) too."""

    __slots__ = ("_data",)

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name: str):
        return self._data.get(name)

    def __getitem__(self, name):
        return self._data[name]

    def get(self, name, default=None):
        return self._data.get(name, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __bool__(self):
        return bool(self._data)

    def __contains__(self, name):
        return name in self._data


def _as_date(value):
    """Coerce an ISO-format date string / datetime/date into datetime.date.

    sqlite stores dates as 'YYYY-MM-DD' TEXT, so expert functions receive ISO
    strings for date-bearing fields; normalizing to real dates centrally lets
    every date-arithmetic site (due_on - today, age in years, X days late)
    work unchanged.  Idempotent: datetime.date / datetime / None / non-date
    values pass through untouched; non-parseable strings are left as-is.
    """
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return value
    return value


def _rowify(value):
    """Recursively wrap dicts / mapping-likes so attribute access works.

    Idempotent: already-wrapped ``_AttrRow`` instances and non-mapping values
    are returned unchanged, so it is safe to apply at every public entry point
    AND at the head of each public function (re-wrapping is a cheap no-op).
    """
    if isinstance(value, _AttrRow):
        return value
    if isinstance(value, dict):
        return _AttrRow({k: _rowify(_as_date(v)) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return [_rowify(v) for v in value]
    if hasattr(value, "keys"):  # dict, sqlite3.Row, or any mapping-like
        data = dict(value)
        return _AttrRow({k: _rowify(_as_date(v)) for k, v in data.items()})
    return value


# --------------------------------------------------------------------------
# Knowledge base
# --------------------------------------------------------------------------

EMERGENCY_SYMPTOMS = {
    # symptom keyword group -> (label, urgency)
    "bloat": ("abdominal swelling", "emergency"),
    "choking": ("choking", "emergency"),
    "seizur": ("seizure", "emergency"),
    "convuls": ("seizure", "emergency"),
    "collapse": ("collapsed", "emergency"),
    "unconscious": ("unconscious", "emergency"),
    "poison": ("possible poisoning", "emergency"),
    "toxic": ("possible poisoning", "emergency"),
    "ingest": ("possible ingestion of toxin/foreign body", "emergency"),
    "hit by": ("hit by vehicle", "emergency"),
    "hit-by": ("hit by vehicle", "emergency"),
    "major bleed": ("major bleeding", "emergency"),
    "uncontrollable bleed": ("major bleeding", "emergency"),
    "can't breathe": ("breathing difficulty", "emergency"),
    "cannot breathe": ("breathing difficulty", "emergency"),
    "gasping": ("breathing difficulty", "emergency"),
    "not breathing": ("not breathing", "emergency"),
    "distress": ("severe distress", "urgent"),
    "severe": ("severe symptom", "urgent"),
    "broken": ("suspected fracture", "urgent"),
    "fracture": ("suspected fracture", "urgent"),
    "cold and shivering": ("hypothermia warning sign", "urgent"),
    "not eating": ("not eating", "watch"),
    "won't eat": ("not eating", "watch"),
    "not drinking": ("not drinking", "watch"),
    "losing weight": ("weight loss", "watch"),
    "loss of appetite": ("loss of appetite", "watch"),
    "letharg": ("lethargy", "watch"),
    "vomit": ("vomiting", "watch"),
    "diarrhea": ("diarrhoea", "watch"),
    "diarrhoea": ("diarrhoea", "watch"),
    "cough": ("coughing", "watch"),
    "sneez": ("sneezing", "watch"),
    "itch": ("itching / skin issue", "watch"),
    "scratch": ("itching / skin issue", "watch"),
    "flea": ("flea / parasite concern", "watch"),
    "tick": ("tick concern", "watch"),
    "worm": ("worm concern", "watch"),
    "limp": ("limping", "watch"),
    "limping": ("limping", "watch"),
    "pale": ("pale gums", "watch"),
    "gum": ("gum issue", "watch"),
    "ear": ("ear issue", "watch"),
    "eye": ("eye issue", "watch"),
    "pee twice": ("urinary concern", "watch"),
    "urinating more": ("urinary concern", "watch"),
    "blood in urine": ("urinary concern", "watch"),
    "constipat": ("constipation", "watch"),
    "pant": ("panting/excessive panting", "watch"),
    "trembl": ("trembling", "watch"),
    "shake": ("shaking/trembling", "watch"),
    "aggress": ("behaviour change / aggression", "watch"),
    "anxious": ("anxiety", "routine"),
    "anxiety": ("anxiety", "routine"),
    "whining": ("whining", "routine"),
    "bark": ("barking behaviour", "routine"),
    "biting": ("biting behaviour", "routine"),
    "scratching": ("scratching", "routine"),
    "destructive": ("destructive behaviour", "routine"),
}

SPECIES_TIPS = {
    "dog": [
        "Dogs need at least 30-60 minutes of exercise daily; adjust for age/breed.",
        "Dental care matters — brush weekly and offer chews to reduce plaque.",
        "Never feed chocolate, grapes, raisins, onions, or xylitol (all toxic to dogs).",
    ],
    "cat": [
        "Cats are obligate carnivores; meat-based proteins are essential.",
        "Provide fresh water every day and clean litter boxes daily.",
        "Never feed chocolate, onions, garlic, or lilies are toxic to cats too.",
    ],
    "bird": [
        "Keep the cage clean, provide fresh water daily, and avoid drafts.",
        "Avoid avocado, chocolate, caffeine, and avocado for birds.",
        "Birds hide illness — any change in eating or droppings warrants a vet check.",
    ],
    "other": [
        "Keep a consistent feeding and cleaning routine.",
        "Any sudden change in behaviour warrants a vet check.",
    ],
}

RESTING_HYDRATION_MARKERS = {
    "dog": "fresh water should always be available; encourage after walks.",
    "cat": "provide multiple water bowls (cats prefer running water).",
    "bird": "change water daily and clean the bowl.",
}


def _species_of(pet) -> str:
    if pet is None:
        return "other"
    s = (pet.species or "other").lower()
    if s in ("dog", "cat", "bird", "other"):
        return s
    return "other"


# --------------------------------------------------------------------------
# Triage
# --------------------------------------------------------------------------


def triage(question: str) -> dict:
    """Classify a question into a triage level + matched symptom label."""
    q = " " + (question or "").lower()
    q = re.sub(r"[^a-z\s']+", " ", q)
    q = " " + re.sub(r"\s+", " ", q) + " "

    matched = []
    for key, (label, level) in EMERGENCY_SYMPTOMS.items():
        # word-boundary match on multi-word triggers and single words
        if re.search(r"\b" + re.escape(key.strip()) + r"\b", q):
            matched.append((label, level))

    levels = {"emergency": 3, "urgent": 2, "watch": 1, "routine": 0}
    best = max((levels[l] for _, l in matched), default=0)
    labels = list(dict.fromkeys(label for label, _ in matched))
    level = {3: "emergency", 2: "urgent", 1: "watch", 0: "routine"}[best]

    return {
        "level": level,
        "matched_symptoms": labels[:4],
        "prompt_vet": level in ("emergency", "urgent"),
    }


EMERGENCY_ACTION = """Red flags detected. Please act fast:
1. Stay calm and keep your pet warm and still.
2. Do NOT give food, water, or any medication unless a vet says so.
3. Contact your vet / nearest animal emergency clinic immediately.
4. If you suspect poisoning (e.g., chocolate, raisins, xylitol, lilies, antifreeze): save the packet and tell the vet exactly what and how much was ingested.
5. For choking or not breathing: begin gentle first aid only if you are trained.
I've listed emergency contacts below — call one right now."""

# --------------------------------------------------------------------------
# Vaccination due logic
# --------------------------------------------------------------------------

_VACCINE_INTERVALS = {
    "rabies": 365,
    "dhpp": 365,
    "dhpp booster": 365,
    "distemper": 365,
    "fvrp": 365,
    "fvrp-fcv": 365,
    "feline leukemia": 365,
    "fiv": 365,
    "kennel cough": 180,
    "bordetella": 180,
    "leptospirosis": 365,
    "heartworm": 365,
}


def vaccination_summary(vaccinations) -> dict:
    """Given an iterable of VaccinationRecord, return due/overdue analysis."""
    vaccinations = _rowify(vaccinations)
    today = dt.date.today()
    upcoming = []
    overdue = []
    uptodate = []
    for v in vaccinations or []:
        due = v.next_due_on
        if not due:
            uptodate.append({"name": v.name, "status": "up-to-date"})
            continue
        days_left = (due - today).days
        if days_left < 0:
            overdue.append(
                {
                    "name": v.name,
                    "due": due.isoformat(),
                    "days_overdue": abs(days_left),
                    "status": "overdue",
                }
            )
        elif days_left <= 30:
            upcoming.append(
                {
                    "name": v.name,
                    "due": due.isoformat(),
                    "days_left": days_left,
                    "status": "due",
                }
            )
        else:
            uptodate.append(
                {
                    "name": v.name,
                    "due": due.isoformat(),
                    "days_left": days_left,
                    "status": "up-to-date",
                }
            )
    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "up_to_date": uptodate,
        "next_due": min([v["due"] for v in overdue + upcoming], default=None),
    }


# --------------------------------------------------------------------------
# Feeding / weight guidance
# --------------------------------------------------------------------------


def feeding_guidance(pet) -> dict:
    """Estimate daily kcal needs + portion hints (Merriam-style RER/weight)."""
    pet = _rowify(pet)
    if pet is None or pet.species not in ("dog", "cat"):
        return {
            "estimate": None,
            "advice": "Provide feed appropriate to your pet's species, age, and activity level.",
        }
    weight = float(pet.weight_kg or 0)
    rer = 70 * (weight**0.75) if weight > 0 else 0
    # Maintenance factor approximation for adult indoor pets
    factor = 1.6 if pet.species == "dog" else 1.2
    mer = rer * factor
    return {
        "estimate_kcal": round(mer),
        "advice": (
            f"Rough daily calorie estimate ≈ {round(mer):,} kcal (RER-based maintenance). "
            "Adjust for age, activity, pregnancy, and body condition. "
            f"Portion by weight: {weight:.1f} kg — use the food label as the starting point and "
            "monitor body condition weekly."
        ),
        "hydration": RESTING_HYDRATION_MARKERS.get(
            pet.species, "Ensure fresh water at all times."
        ),
    }


# --------------------------------------------------------------------------
# Care-task advice per category
# --------------------------------------------------------------------------

_CARE_ADVICE = {
    "feeding": "Stick to a fixed schedule, measure portions by weight, and keep treats under 10% of daily calories.",
    "exercise": "Match intensity to age/breed; regular short sessions beat one long session. Rest if panting heavily.",
    "grooming": "Brush regularly to reduce mats and check for fleas, ticks, and skin issues while you groom.",
    "medication": "Give medications at the same time daily; if a dose is missed more than halfway, ask your vet.",
    "hygiene": "Clean food/water bowls daily and keep the sleeping area fresh; disinfect food bowls regularly.",
    "care": "Consistency is key — a predictable routine lowers stress for pets.",
}

# --------------------------------------------------------------------------
# Care schedule due status
# --------------------------------------------------------------------------


def schedule_status(schedule) -> str:
    schedule = _rowify(schedule)
    if not schedule.active:
        return "inactive"
    if schedule.next_due_on is None:
        return "active"  # recurring, no explicit date
    if (schedule.next_due_on - dt.date.today()).days <= 3:
        return "due"
    return "upcoming"


# --------------------------------------------------------------------------
# Pet health summary used to contextualise answers
# --------------------------------------------------------------------------


def pet_context(pet, vaccinations=None, weight_log=None, records=None, schedules=None):
    pet = _rowify(pet)
    vaccinations = _rowify(vaccinations)
    weight_log = _rowify(weight_log)
    records = _rowify(records)
    schedules = _rowify(schedules)
    if pet is None:
        return {}
    return {
        "name": pet.name,
        "species": pet.species,
        "breed": pet.breed,
        "weight_kg": pet.weight_kg,
        "age_years": pet_age(pet),
        "vaccinations": vaccination_summary(vaccinations or []),
        "care": [
            {"task": c.task, "category": c.category, "status": schedule_status(c)}
            for c in (schedules or [])
        ],
        "recent_records": [
            {"title": r.title, "type": r.record_type} for r in (records or [])
        ][:5],
    }


def pet_age(pet) -> float | None:
    dob = (
        pet.get("date_of_birth")
        if isinstance(pet, dict)
        else getattr(pet, "date_of_birth", None)
    )
    if not dob:
        return None
    if isinstance(dob, str):
        dob = dt.date.fromisoformat(dob)
    days = (dt.date.today() - dob).days
    return round(days / 365.25, 1)


# --------------------------------------------------------------------------
# Question matcher
# --------------------------------------------------------------------------


def answer_question(question: str, pet=None) -> dict:
    """Produce a structured, deterministic answer + triage for a question."""
    pet = _rowify(pet)
    q = (question or "").lower()
    tri = triage(q)
    species = _species_of(pet)
    pet_name = pet.name if pet is not None else "your pet"

    # Emergency triage overrides everything
    if tri["level"] == "emergency":
        return {
            "triage": tri,
            "answer": EMERGENCY_ACTION,
            "disclaimer": "This is general guidance, not veterinary medical advice. For emergencies call your vet immediately.",
            "topics": ["emergency"],
        }

    answer_parts = []
    topics = []

    if any(
        k in q
        for k in (
            "needle",
            "shot",
            "vaccin",
            "immun",
            "booster",
            "rabies",
            "dhpp",
            "fvrp",
        )
    ):
        topics.append("vaccination")
        answer_parts.append(vaccination_advice(pet))

    if any(
        k in q
        for k in (
            "eat",
            "feeding",
            "food",
            "feed",
            "diet",
            "calorie",
            "portion",
            "hungry",
            "dry food",
            "wet food",
            "how much",
        )
    ):
        topics.append("feeding")
        g = feeding_guidance(pet)
        answer_parts.append(
            g["advice"] + (" \u2022 " + g["hydration"] if g.get("hydration") else "")
        )

    if any(
        k in q
        for k in (
            "weight",
            "fat",
            "thin",
            "overweight",
            "underweight",
            "body condition",
            "losing",
            "gain",
        )
    ):
        topics.append("weight")
        w = float(pet.weight_kg or 0) if pet is not None else 0
        if pet is not None and w:
            if pet.species == "dog" and w > 30:
                answer_parts.append(
                    f"{pet_name} looks above a typical comfort range for many dogs — track weight weekly and check with your vet about a tailored plan."
                )
            elif pet.species == "cat" and w > 6:
                answer_parts.append(
                    f"{pet_name}'s weight is on the higher side for cats; a vet-supervised gradual adjustment is a good idea."
                )
            else:
                answer_parts.append(
                    f"{pet_name} is {w:.1f} kg at last log — keep a weekly weight log to watch for trends."
                )
        answer_parts.append(
            "Sudden weight loss without diet change is a vet-worthy sign."
        )

    if any(
        k in q
        for k in (
            "schedul",
            "routine",
            "when should i",
            "clean",
            "brush",
            "bath",
            "groom",
            "walk",
            "exercise",
            "play",
            "litter",
        )
    ):
        topics.append("care_routine")
        for cat in ("feeding", "exercise", "grooming", "medication", "hygiene", "care"):
            if any(k in q for k in _CARE_ADVICE[cat].split()[0:1]):
                answer_parts.append(_CARE_ADVICE[cat])
                break
        else:
            answer_parts.append(_CARE_ADVICE["care"])

    if any(
        k in q
        for k in (
            "bite",
            "choco",
            "poison",
            "toxic",
            "grape",
            "onion",
            "xylitol",
            "lily",
            "toxic plants",
        )
    ):
        topics.append("safety")
        answer_parts.append(
            "Common pet toxins: chocolate, xylitol, grapes/raisins, onions/garlic, lilies (cats), avocado, alcohol, antifreeze. Contact your vet or a pet poison line immediately if ingested."
        )

    if any(
        k in q
        for k in (
            "house",
            "training",
            "crate",
            "toilet",
            "potty",
            "behavio",
            "bark",
            "scratch furniture",
        )
    ):
        topics.append("training")
        answer_parts.append(
            "Positive-reinforcement training works best: reward desired behaviour, keep sessions short (5-10 min), and stay consistent every day."
        )

    if any(
        k in q
        for k in (
            "sick",
            "ill",
            "fever",
            "lazy",
            "sad",
            "sleep",
            "letharg",
            "hiding",
            "not himself",
        )
    ):
        topics.append("health_watch")
        answer_parts.append(
            "If {n} shows low energy, changes in appetite/thirst, or hiding, monitor for 24 hours but book a vet check sooner rather than later — pets hide illness early."
        )

    if not answer_parts:
        topics = ["general"]
        if pet is not None:
            answer_parts.append(
                f"Here are some care tips for {pet_name} ({pet.species}):"
            )
            answer_parts.extend(SPECIES_TIPS.get(species, SPECIES_TIPS["other"]))
        else:
            answer_parts.append(
                "Tell me which pet this is about (select a pet on the left) and I can give more specific "
                "feeding, vaccination, and care advice. General tips: keep fresh water always, feed measured "
                "portions, stick to the vaccine schedule, and give plenty of exercise and enrichment."
            )

    if tri["level"] == "urgent":
        answer_parts.append(
            "\nSeek veterinary care promptly — symptoms here are concerning."
        )
    if tri["level"] == "watch":
        answer_parts.append(
            "\nKeep a close watch on this — book a vet visit if it lasts more than a day."
        )

    return {
        "triage": tri,
        "answer": "\n".join(answer_parts),
        "disclaimer": "Purpose: general pet-care education, not a diagnosis. Always confirm with your veterinarian.",
        "topics": topics,
    }


def vaccination_advice(pet) -> str:
    pet = _rowify(pet)
    if pet is None:
        return "Core vaccines for dogs: DHPP + Rabies. Cats: FVRCP + Rabies. Revaccinate per your vet's protocol and local laws."
    s = vaccination_summary(pet.vaccinations)
    lines = [f"Vaccination status for {pet.name}:"]
    if s["overdue"]:
        lines.append(
            " - Overdue: "
            + ", ".join(f"{v['name']} ({v['days_overdue']}d)" for v in s["overdue"])
        )
    if s["upcoming"]:
        lines.append(
            " - Due soon: "
            + ", ".join(f"{v['name']} in {v['days_left']}d" for v in s["upcoming"])
        )
    if s["up_to_date"]:
        names = ", ".join(v["name"] for v in s["up_to_date"][:4])
        lines.append(f" - Up-to-date: {names}")
    lines.append("Keep records and schedule boosters with your vet.")
    return "\n".join(lines)
