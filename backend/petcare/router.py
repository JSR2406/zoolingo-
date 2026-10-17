"""FastAPI router for the PetCare platform.

Endpoints (all under ``/api/petcare``):
  - pets        CRUD + age, vaccination, weight, health CRUD
  - care        schedules + vet contacts CRUD
  - expert      rule-based triage/expert advice (SSE chat stream + non-stream)

Data access goes through the stdlib ``sqlite3`` layer in ``backend.petcare.database``
(pure Python — no SQLAlchemy, no ORM).
"""
import datetime as dt
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from petcare import schemas
from petcare import expert_engine
from petcare.database import (
    delete_row,
    execute,
    get_conn,
    query_all,
    query_one,
)

logger = logging.getLogger(__name__)

petcare_router = APIRouter(prefix="/api/petcare", tags=["petcare"])


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------


def _row_out(row) -> dict:
    """Turn a sqlite3.Row into a plain dict (for JSON-serialisable responses)."""
    return dict(row)


def _get_pet_or_404(pet_id: int):
    row = query_one("SELECT * FROM pets WHERE id = ?", (pet_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return row


def _get_vacc_or_404(vacc_id: int):
    row = query_one("SELECT * FROM vaccination_records WHERE id = ?", (vacc_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Vaccination record not found")
    return row


def _with_age(pet_row) -> dict:
    d = _row_out(pet_row)
    d["age_years"] = expert_engine.pet_age(d)
    return d


# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------


@petcare_router.get("/pets", response_model=list[schemas.PetOut])
def list_pets():
    return [_with_age(p) for p in query_all("SELECT * FROM pets ORDER BY name")]


@petcare_router.post("/pets", response_model=schemas.PetOut, status_code=201)
def create_pet(payload: schemas.PetCreate):
    _id = execute(
        "INSERT INTO pets (name, species, breed, gender, date_of_birth, weight_kg, "
        "microchip_id, avatar_emoji, notes) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            payload.name,
            payload.species,
            payload.breed,
            payload.gender,
            payload.date_of_birth,
            payload.weight_kg,
            payload.microchip_id,
            payload.avatar_emoji,
            payload.notes,
        ),
    )
    return _with_age(query_one("SELECT * FROM pets WHERE id = ?", (_id,)))


@petcare_router.get("/pets/{pet_id}", response_model=schemas.PetOut)
def get_pet(pet_id: int):
    _get_pet_or_404(pet_id)
    return _with_age(query_one("SELECT * FROM pets WHERE id = ?", (pet_id,)))


@petcare_router.put("/pets/{pet_id}", response_model=schemas.PetOut)
def update_pet(pet_id: int, payload: schemas.PetUpdate):
    _get_pet_or_404(pet_id)
    fields = [
        "name",
        "species",
        "breed",
        "gender",
        "date_of_birth",
        "weight_kg",
        "microchip_id",
        "avatar_emoji",
        "notes",
    ]
    sets = []
    values = []
    for f in fields:
        v = getattr(payload, f)
        if v is not None:
            sets.append(f"{f} = ?")
            values.append(v)
    values.append(pet_id)
    if sets:
        execute(f"UPDATE pets SET {', '.join(sets)} WHERE id = ?", tuple(values))
    return _with_age(query_one("SELECT * FROM pets WHERE id = ?", (pet_id,)))


@petcare_router.delete("/pets/{pet_id}", status_code=204)
def delete_pet(pet_id: int):
    _get_pet_or_404(pet_id)
    delete_row("DELETE FROM pets WHERE id = ?", (pet_id,))


# ---------------------------------------------------------------------------
# Vaccinations
# ---------------------------------------------------------------------------


@petcare_router.get(
    "/pets/{pet_id}/vaccinations", response_model=list[schemas.VaccinationOut]
)
def list_vaccinations(pet_id: int):
    _get_pet_or_404(pet_id)
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM vaccination_records WHERE pet_id = ? ORDER BY next_due_on IS NULL, next_due_on",
            (pet_id,),
        )
    ]


@petcare_router.post(
    "/pets/{pet_id}/vaccinations",
    response_model=schemas.VaccinationOut,
    status_code=201,
)
def create_vaccination(pet_id: int, payload: schemas.VaccinationCreate):
    _get_pet_or_404(pet_id)
    _id = execute(
        "INSERT INTO vaccination_records (pet_id, name, administered_on, next_due_on, "
        "administered_at, notes) VALUES (?,?,?,?,?,?)",
        (
            pet_id,
            payload.name,
            payload.administered_on,
            payload.next_due_on,
            payload.administered_at,
            payload.notes,
        ),
    )
    return dict(query_one("SELECT * FROM vaccination_records WHERE id = ?", (_id,)))


@petcare_router.delete("/vaccinations/{vacc_id}", status_code=204)
def delete_vaccination(vacc_id: int):
    _get_vacc_or_404(vacc_id)
    delete_row("DELETE FROM vaccination_records WHERE id = ?", (vacc_id,))


# ---------------------------------------------------------------------------
# Weight log
# ---------------------------------------------------------------------------


@petcare_router.get("/pets/{pet_id}/weights", response_model=list[schemas.WeightOut])
def list_weights(pet_id: int):
    _get_pet_or_404(pet_id)
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM weight_log WHERE pet_id = ? ORDER BY logged_on DESC",
            (pet_id,),
        )
    ]


@petcare_router.post(
    "/pets/{pet_id}/weights", response_model=schemas.WeightOut, status_code=201
)
def create_weight(pet_id: int, payload: schemas.WeightCreate):
    _get_pet_or_404(pet_id)
    logged_on = payload.logged_on or dt.date.today()
    _id = execute(
        "INSERT INTO weight_log (pet_id, weight_kg, logged_on) VALUES (?,?,?)",
        (pet_id, payload.weight_kg, logged_on),
    )
    execute("UPDATE pets SET weight_kg = ? WHERE id = ?", (payload.weight_kg, pet_id))
    return dict(query_one("SELECT * FROM weight_log WHERE id = ?", (_id,)))


# ---------------------------------------------------------------------------
# Health records
# ---------------------------------------------------------------------------


@petcare_router.get(
    "/pets/{pet_id}/health-records", response_model=list[schemas.HealthRecordOut]
)
def list_health_records(pet_id: int):
    _get_pet_or_404(pet_id)
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM health_records WHERE pet_id = ? ORDER BY recorded_on DESC",
            (pet_id,),
        )
    ]


@petcare_router.post(
    "/pets/{pet_id}/health-records",
    response_model=schemas.HealthRecordOut,
    status_code=201,
)
def create_health_record(pet_id: int, payload: schemas.HealthRecordCreate):
    _get_pet_or_404(pet_id)
    _id = execute(
        "INSERT INTO health_records (pet_id, record_type, title, description, recorded_on) "
        "VALUES (?,?,?,?,?)",
        (
            pet_id,
            payload.record_type,
            payload.title,
            payload.description,
            payload.recorded_on or dt.date.today(),
        ),
    )
    return dict(query_one("SELECT * FROM health_records WHERE id = ?", (_id,)))


@petcare_router.delete("/health-records/{record_id}", status_code=204)
def delete_health_record(record_id: int):
    if not delete_row("DELETE FROM health_records WHERE id = ?", (record_id,)):
        raise HTTPException(status_code=404, detail="Health record not found")


# ---------------------------------------------------------------------------
# Care schedules
# ---------------------------------------------------------------------------


@petcare_router.get(
    "/pets/{pet_id}/care-schedules", response_model=list[schemas.CareScheduleOut]
)
def list_care_schedules(pet_id: int):
    _get_pet_or_404(pet_id)
    out = []
    for r in query_all(
        "SELECT * FROM care_schedules WHERE pet_id = ? ORDER BY active DESC, id",
        (pet_id,),
    ):
        d = dict(r)
        d["status"] = expert_engine.schedule_status(d)
        out.append(d)
    return out


@petcare_router.post(
    "/pets/{pet_id}/care-schedules",
    response_model=schemas.CareScheduleOut,
    status_code=201,
)
def create_care_schedule(pet_id: int, payload: schemas.CareScheduleCreate):
    _get_pet_or_404(pet_id)
    _id = execute(
        "INSERT INTO care_schedules (pet_id, task, category, frequency, time_of_day, "
        "next_due_on, active) VALUES (?,?,?,?,?,?,?)",
        (
            pet_id,
            payload.task,
            payload.category,
            payload.frequency,
            payload.time_of_day,
            payload.next_due_on,
            int(payload.active),
        ),
    )
    d = dict(query_one("SELECT * FROM care_schedules WHERE id = ?", (_id,)))
    d["status"] = expert_engine.schedule_status(d)
    return d


@petcare_router.put(
    "/care-schedules/{schedule_id}", response_model=schemas.CareScheduleOut
)
def update_care_schedule(schedule_id: int, payload: schemas.CareScheduleUpdate):
    row = query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Care schedule not found")
    fields = ["task", "category", "frequency", "time_of_day", "next_due_on", "active"]
    sets = []
    values = []
    for f in fields:
        v = getattr(payload, f)
        if v is not None:
            sets.append(f"{f} = ?")
            values.append(v)
    values.append(schedule_id)
    if sets:
        execute(
            f"UPDATE care_schedules SET {', '.join(sets)} WHERE id = ?", tuple(values)
        )
    d = dict(query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,)))
    d["status"] = expert_engine.schedule_status(d)
    return d


@petcare_router.post(
    "/care-schedules/{schedule_id}/complete", response_model=schemas.CareScheduleOut
)
def complete_care_schedule(schedule_id: int):
    """Mark a care task done; roll next_due_on forward for recurring tasks."""
    row = query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Care schedule not found")
    delta = {
        "daily": 1,
        "weekly": 7,
        "biweekly": 14,
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
    }.get(row["frequency"], 1)
    due = row["next_due_on"]
    if due:
        d = dt.date.fromisoformat(due)
        while d <= dt.date.today():
            d += dt.timedelta(days=delta)
        new_due = d
    else:
        new_due = dt.date.today() + dt.timedelta(days=delta)
    execute(
        "UPDATE care_schedules SET next_due_on = ? WHERE id = ?", (new_due, schedule_id)
    )
    out = dict(query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,)))
    out["status"] = expert_engine.schedule_status(out)
    return out


@petcare_router.delete("/care-schedules/{schedule_id}", status_code=204)
def delete_care_schedule(schedule_id: int):
    if not delete_row("DELETE FROM care_schedules WHERE id = ?", (schedule_id,)):
        raise HTTPException(status_code=404, detail="Care schedule not found")


# ---------------------------------------------------------------------------
# Vet contacts
# ---------------------------------------------------------------------------


@petcare_router.get("/vets", response_model=list[schemas.VetOut])
def list_vets():
    return [
        dict(r)
        for r in query_all("SELECT * FROM vet_contacts ORDER BY emergency DESC, name")
    ]


@petcare_router.post("/vets", response_model=schemas.VetOut, status_code=201)
def create_vet(payload: schemas.VetCreate):
    _id = execute(
        "INSERT INTO vet_contacts (name, phone, address, specialty, hours, emergency) "
        "VALUES (?,?,?,?,?,?)",
        (
            payload.name,
            payload.phone,
            payload.address,
            payload.specialty,
            payload.hours,
            int(payload.emergency),
        ),
    )
    return dict(query_one("SELECT * FROM vet_contacts WHERE id = ?", (_id,)))


@petcare_router.delete("/vets/{vet_id}", status_code=204)
def delete_vet(vet_id: int):
    if not delete_row("DELETE FROM vet_contacts WHERE id = ?", (vet_id,)):
        raise HTTPException(status_code=404, detail="Vet contact not found")


# ---------------------------------------------------------------------------
# Expert (rule-based)
# ---------------------------------------------------------------------------


@petcare_router.post("/expert/advice")
def expert_advice(payload: schemas.ExpertAsk):
    """Rule-based pet care expert — answers a question with triage + advice."""
    pet = _get_pet_or_404(payload.pet_id) if payload.pet_id else None
    result = expert_engine.answer_question(payload.question, pet=pet)
    return {
        "question": payload.question,
        **result,
        "pet": (
            {"id": pet["id"], "name": pet["name"], "species": pet["species"]}
            if pet
            else None
        ),
    }


@petcare_router.post("/expert/chat")
def expert_chat(payload: schemas.ExpertAsk):
    """Non-streaming expert chat reply."""
    pet = _get_pet_or_404(payload.pet_id) if payload.pet_id else None
    result = expert_engine.answer_question(payload.question, pet=pet)
    return {
        "conversation_id": payload.conversation_id,
        "pet": ({"id": pet["id"], "name": pet["name"]} if pet else None),
        "reply": result["answer"],
        "triage": result["triage"],
        "topics": result["topics"],
        "disclaimer": result["disclaimer"],
    }


@petcare_router.post("/expert/chat/stream")
def expert_chat_stream(payload: schemas.ExpertAsk):
    """SSE streaming chat reply — token-by-token deltas then a done event."""
    pet = _get_pet_or_404(payload.pet_id) if payload.pet_id else None
    result = expert_engine.answer_question(payload.question, pet=pet)
    text = result["answer"]

    async def gen():
        for i in range(0, len(text), 4):
            yield f"data: {json.dumps({'type': 'token', 'content': text[i:i+4]})}\n\n"
        done = {
            "type": "done",
            "triage": result["triage"],
            "topics": result["topics"],
            "disclaimer": result["disclaimer"],
        }
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@petcare_router.get("/dashboard")
def dashboard():
    """Aggregate overview: pets, due vaccines, due care tasks, emergency vets."""
    pets = [_with_age(p) for p in query_all("SELECT * FROM pets ORDER BY name")]
    due_vax = []
    due_care = []

    for p in pets:
        triage_vax = expert_engine.vaccination_summary(
            [
                dict(r)
                for r in query_all(
                    "SELECT * FROM vaccination_records WHERE pet_id = ?", (p["id"],)
                )
            ]
        )
        due_vax.extend(triage_vax.get("overdue", []))
        due_vax.extend(triage_vax.get("upcoming", []))

        for c in query_all(
            "SELECT * FROM care_schedules WHERE pet_id = ? AND active = 1", (p["id"],)
        ):
            d = dict(c)
            if expert_engine.schedule_status(d) in ("due", "overdue"):
                due_care.append(
                    {
                        "pet_id": p["id"],
                        "pet": p["name"],
                        "task": d["task"],
                        "category": d["category"],
                        "status": expert_engine.schedule_status(d),
                    }
                )

    return {
        "total_pets": len(pets),
        "pets": pets,
        "due_vaccinations": due_vax[:12],
        "due_care_tasks": due_care[:12],
        "emergency_vets": [
            dict(r)
            for r in query_all(
                "SELECT * FROM vet_contacts WHERE emergency = 1 ORDER BY name"
            )
        ],
    }
