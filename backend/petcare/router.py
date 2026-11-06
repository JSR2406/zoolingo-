"""FastAPI router for the PetCare platform.

Endpoints (all under ``/api/petcare``):
  - pets        CRUD + age, vaccination, weight, health CRUD
  - care        schedules + vet contacts CRUD
  - expert      rule-based triage/expert advice (SSE chat stream + non-stream)
  - conversations   persistent chat sessions per pet
  - messages        chat messages within conversations
  - voice-conversions   audio translation events
  - locations       GPS location tracking + geofence checks
All endpoints require authentication and enforce user ownership.
Data access goes through the stdlib ``sqlite3`` layer in ``backend.petcare.database``
(pure Python — no SQLAlchemy, no ORM).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from auth import get_current_user
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
# Helpers
# ---------------------------------------------------------------------------

def _row_out(row) -> dict:
    """Turn a sqlite3.Row into a plain dict (for JSON-serialisable responses)."""
    return dict(row) if row else {}


def _get_pet_or_404(pet_id: int, user_id: str):
    row = query_one(
        "SELECT * FROM pets WHERE id = ? AND user_id = ?", (pet_id, user_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return row


def _get_vacc_or_404(vacc_id: int, user_id: str):
    row = query_one(
        "SELECT * FROM vaccination_records WHERE id = ? AND user_id = ?",
        (vacc_id, user_id),
    )
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
def list_pets(current_user: dict = Depends(get_current_user)):
    """List all pets for the authenticated user."""
    user_id = str(current_user["id"])
    return [
        _with_age(p) for p in query_all("SELECT * FROM pets WHERE user_id = ? ORDER BY name", (user_id,))
    ]


@petcare_router.post("/pets", response_model=schemas.PetOut, status_code=201)
def create_pet(payload: schemas.PetCreate, current_user: dict = Depends(get_current_user)):
    """Create a new pet profile for the authenticated user."""
    user_id = str(current_user["id"])
    _id = execute(
        "INSERT INTO pets (user_id, name, species, breed, gender, date_of_birth, weight_kg, "
        "microchip_id, avatar_emoji, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            user_id,
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
def get_pet(pet_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single pet by ID (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    return _with_age(query_one("SELECT * FROM pets WHERE id = ?", (pet_id,)))


@petcare_router.put("/pets/{pet_id}", response_model=schemas.PetOut)
def update_pet(
    pet_id: int,
    payload: schemas.PetUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a pet profile (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
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
        sets.append("updated_at = datetime('now')")
        execute(f"UPDATE pets SET {', '.join(sets)} WHERE id = ?", tuple(values))
    return _with_age(query_one("SELECT * FROM pets WHERE id = ?", (pet_id,)))


@petcare_router.delete("/pets/{pet_id}", status_code=204)
def delete_pet(pet_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a pet profile (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    delete_row("DELETE FROM pets WHERE id = ? AND user_id = ?", (pet_id, user_id))


# ---------------------------------------------------------------------------
# Vaccinations
# ---------------------------------------------------------------------------


@petcare_router.get("/pets/{pet_id}/vaccinations", response_model=list[schemas.VaccinationOut])
def list_vaccinations(pet_id: int, current_user: dict = Depends(get_current_user)):
    """List vaccinations for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM vaccination_records WHERE pet_id = ? AND user_id = ? ORDER BY next_due_on IS NULL, next_due_on",
            (pet_id, user_id),
        )
    ]


@petcare_router.post("/pets/{pet_id}/vaccinations", response_model=schemas.VaccinationOut, status_code=201)
def create_vaccination(
    pet_id: int,
    payload: schemas.VaccinationCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a vaccination record for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    _id = execute(
        "INSERT INTO vaccination_records (pet_id, user_id, name, administered_on, next_due_on, "
        "administered_at, notes) VALUES (?,?,?,?,?,?,?)",
        (
            pet_id,
            user_id,
            payload.name,
            payload.administered_on,
            payload.next_due_on,
            payload.administered_at,
            payload.notes,
        ),
    )
    return dict(query_one("SELECT * FROM vaccination_records WHERE id = ?", (_id,)))


@petcare_router.delete("/vaccinations/{vacc_id}", status_code=204)
def delete_vaccination(vacc_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a vaccination record (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_vacc_or_404(vacc_id, user_id)
    delete_row("DELETE FROM vaccination_records WHERE id = ? AND user_id = ?", (vacc_id, user_id))


# ---------------------------------------------------------------------------
# Weight log
# ---------------------------------------------------------------------------


@petcare_router.get("/pets/{pet_id}/weights", response_model=list[schemas.WeightOut])
def list_weights(pet_id: int, current_user: dict = Depends(get_current_user)):
    """List weight logs for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM weight_log WHERE pet_id = ? AND user_id = ? ORDER BY logged_on DESC",
            (pet_id, user_id),
        )
    ]


@petcare_router.post("/pets/{pet_id}/weights", response_model=schemas.WeightOut, status_code=201)
def create_weight(
    pet_id: int,
    payload: schemas.WeightCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a weight log entry for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    logged_on = payload.logged_on or dt.date.today()
    _id = execute(
        "INSERT INTO weight_log (pet_id, user_id, weight_kg, logged_on) VALUES (?,?,?,?)",
        (pet_id, user_id, payload.weight_kg, logged_on),
    )
    execute("UPDATE pets SET weight_kg = ? WHERE id = ?", (payload.weight_kg, pet_id))
    return dict(query_one("SELECT * FROM weight_log WHERE id = ?", (_id,)))


# ---------------------------------------------------------------------------
# Health records
# ---------------------------------------------------------------------------


@petcare_router.get("/pets/{pet_id}/health-records", response_model=list[schemas.HealthRecordOut])
def list_health_records(pet_id: int, current_user: dict = Depends(get_current_user)):
    """List health records for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM health_records WHERE pet_id = ? AND user_id = ? ORDER BY recorded_on DESC",
            (pet_id, user_id),
        )
    ]


@petcare_router.post("/pets/{pet_id}/health-records", response_model=schemas.HealthRecordOut, status_code=201)
def create_health_record(
    pet_id: int,
    payload: schemas.HealthRecordCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a health record for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    _id = execute(
        "INSERT INTO health_records (pet_id, user_id, record_type, title, description, recorded_on) "
        "VALUES (?,?,?,?,?,?)",
        (
            pet_id,
            user_id,
            payload.record_type,
            payload.title,
            payload.description,
            payload.recorded_on or dt.date.today(),
        ),
    )
    return dict(query_one("SELECT * FROM health_records WHERE id = ?", (_id,)))


@petcare_router.delete("/health-records/{record_id}", status_code=204)
def delete_health_record(record_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a health record (owner-isolated)."""
    user_id = str(current_user["id"])
    if not delete_row("DELETE FROM health_records WHERE id = ? AND user_id = ?", (record_id, user_id)):
        raise HTTPException(status_code=404, detail="Health record not found")


# ---------------------------------------------------------------------------
# Care schedules
# ---------------------------------------------------------------------------


@petcare_router.get("/pets/{pet_id}/care-schedules", response_model=list[schemas.CareScheduleOut])
def list_care_schedules(pet_id: int, current_user: dict = Depends(get_current_user)):
    """List care schedules for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    out = []
    for r in query_all(
        "SELECT * FROM care_schedules WHERE pet_id = ? AND user_id = ? ORDER BY active DESC, id",
        (pet_id, user_id),
    ):
        d = dict(r)
        d["status"] = expert_engine.schedule_status(d)
        out.append(d)
    return out


@petcare_router.post("/pets/{pet_id}/care-schedules", response_model=schemas.CareScheduleOut, status_code=201)
def create_care_schedule(
    pet_id: int,
    payload: schemas.CareScheduleCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a care schedule for a pet (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(pet_id, user_id)
    _id = execute(
        "INSERT INTO care_schedules (pet_id, user_id, task, category, frequency, time_of_day, "
        "next_due_on, active) VALUES (?,?,?,?,?,?,?,?)",
        (
            pet_id,
            user_id,
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


@petcare_router.put("/care-schedules/{schedule_id}", response_model=schemas.CareScheduleOut)
def update_care_schedule(
    schedule_id: int,
    payload: schemas.CareScheduleUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a care schedule (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one(
        "SELECT * FROM care_schedules WHERE id = ? AND user_id = ?",
        (schedule_id, user_id),
    )
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
        sets.append("updated_at = datetime('now')")
        execute(f"UPDATE care_schedules SET {', '.join(sets)} WHERE id = ?", tuple(values))
    d = dict(query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,)))
    d["status"] = expert_engine.schedule_status(d)
    return d


@petcare_router.post("/care-schedules/{schedule_id}/complete", response_model=schemas.CareScheduleOut)
def complete_care_schedule(
    schedule_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Mark a care task done; roll next_due_on forward for recurring tasks."""
    user_id = str(current_user["id"])
    row = query_one(
        "SELECT * FROM care_schedules WHERE id = ? AND user_id = ?",
        (schedule_id, user_id),
    )
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
        "UPDATE care_schedules SET next_due_on = ? WHERE id = ?",
        (new_due, schedule_id),
    )
    out = dict(query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,)))
    out["status"] = expert_engine.schedule_status(out)
    return out


@petcare_router.delete("/care-schedules/{schedule_id}", status_code=204)
def delete_care_schedule(
    schedule_id: int, current_user: dict = Depends(get_current_user)
):
    """Delete a care schedule (owner-isolated)."""
    user_id = str(current_user["id"])
    if not delete_row("DELETE FROM care_schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id)):
        raise HTTPException(status_code=404, detail="Care schedule not found")


# ---------------------------------------------------------------------------
# Medication schedules
# ---------------------------------------------------------------------------


@petcare_router.get("/medication-schedules", response_model=list[schemas.MedicationScheduleOut])
def list_medication_schedules(
    pet_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List medication schedules for the authenticated user, optionally filtered by pet."""
    user_id = str(current_user["id"])
    if pet_id:
        _get_pet_or_404(pet_id, user_id)
        return [
            dict(r)
            for r in query_all(
                "SELECT * FROM medication_schedules WHERE user_id = ? AND pet_id = ? ORDER BY active DESC, id",
                (user_id, pet_id),
            )
        ]
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM medication_schedules WHERE user_id = ? ORDER BY active DESC, id",
            (user_id,),
        )
    ]


@petcare_router.post("/medication-schedules", response_model=schemas.MedicationScheduleOut, status_code=201)
def create_medication_schedule(
    payload: schemas.MedicationScheduleCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a medication schedule (owner-isolated)."""
    user_id = str(current_user["id"])
    _get_pet_or_404(payload.pet_id, user_id)
    _id = execute(
        "INSERT INTO medication_schedules (user_id, pet_id, medication_name, dosage, frequency, time_of_day, next_due_on, active) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            user_id,
            payload.pet_id,
            payload.medication_name,
            payload.dosage,
            payload.frequency,
            payload.time_of_day,
            payload.next_due_on.isoformat() if payload.next_due_on else None,
            int(payload.active),
        ),
    )
    return dict(query_one("SELECT * FROM medication_schedules WHERE id = ?", (_id,)))


@petcare_router.put("/medication-schedules/{schedule_id}", response_model=schemas.MedicationScheduleOut)
def update_medication_schedule(
    schedule_id: int,
    payload: schemas.MedicationScheduleUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a medication schedule (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one("SELECT user_id FROM medication_schedules WHERE id = ?", (schedule_id,))
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Medication schedule not found")
    sets = []
    values = []
    for f in ["medication_name", "dosage", "frequency", "time_of_day", "next_due_on", "active"]:
        v = getattr(payload, f)
        if v is not None:
            if f == "next_due_on":
                sets.append(f"{f} = ?")
                values.append(v.isoformat())
            elif f == "active":
                sets.append(f"{f} = ?")
                values.append(int(v))
            else:
                sets.append(f"{f} = ?")
                values.append(v)
    values.append(schedule_id)
    if sets:
        sets.append("updated_at = datetime('now')")
        execute(
            f"UPDATE medication_schedules SET {', '.join(sets)} WHERE id = ?",
            tuple(values),
        )
    return dict(query_one("SELECT * FROM medication_schedules WHERE id = ?", (schedule_id,)))


@petcare_router.delete("/medication-schedules/{schedule_id}", status_code=204)
def delete_medication_schedule(
    schedule_id: int, current_user: dict = Depends(get_current_user)
):
    """Delete a medication schedule (owner-isolated)."""
    user_id = str(current_user["id"])
    if not delete_row("DELETE FROM medication_schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id)):
        raise HTTPException(status_code=404, detail="Medication schedule not found")


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


@petcare_router.get("/reminders", response_model=list[schemas.ReminderOut])
def list_reminders(
    pet_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List reminders for the authenticated user, optionally filtered by pet."""
    user_id = str(current_user["id"])
    if pet_id:
        _get_pet_or_404(pet_id, user_id)
        return [
            dict(r)
            for r in query_all(
                "SELECT * FROM reminders WHERE user_id = ? AND pet_id = ? ORDER BY target_date DESC, id",
                (user_id, pet_id),
            )
        ]
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM reminders WHERE user_id = ? ORDER BY target_date DESC, id",
            (user_id,),
        )
    ]


@petcare_router.post("/reminders", response_model=schemas.ReminderOut, status_code=201)
def create_reminder(
    payload: schemas.ReminderCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a reminder (owner-isolated)."""
    user_id = str(current_user["id"])
    if payload.pet_id:
        _get_pet_or_404(payload.pet_id, user_id)
    _id = execute(
        "INSERT INTO reminders (user_id, pet_id, medication_schedule_id, title, description, kind, target_date, delivered_at, delivery_method, status) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            user_id,
            payload.pet_id,
            payload.medication_schedule_id if hasattr(payload, 'medication_schedule_id') else None,
            payload.title,
            payload.description,
            payload.kind,
            payload.target_date.isoformat() if payload.target_date else None,
            payload.delivered_at,
            payload.delivery_method,
            payload.status,
        ),
    )
    return dict(query_one("SELECT * FROM reminders WHERE id = ?", (_id,)))


@petcare_router.put("/reminders/{reminder_id}", response_model=schemas.ReminderOut)
def update_reminder(
    reminder_id: int,
    payload: schemas.ReminderUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a reminder (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one("SELECT user_id FROM reminders WHERE id = ?", (reminder_id,))
    if not row or row["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Reminder not found")
    sets = []
    values = []
    for f in ["title", "description", "kind", "target_date", "delivered_at", "delivery_method", "status"]:
        v = getattr(payload, f)
        if v is not None:
            if f == "target_date":
                sets.append(f"{f} = ?")
                values.append(v.isoformat())
            else:
                sets.append(f"{f} = ?")
                values.append(v)
    values.append(reminder_id)
    if sets:
        sets.append("updated_at = datetime('now')")
        execute(
            f"UPDATE reminders SET {', '.join(sets)} WHERE id = ?",
            tuple(values),
        )
    return dict(query_one("SELECT * FROM reminders WHERE id = ?", (reminder_id,)))


@petcare_router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: int, current_user: dict = Depends(get_current_user)
):
    """Delete a reminder (owner-isolated)."""
    user_id = str(current_user["id"])
    if not delete_row("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id)):
        raise HTTPException(status_code=404, detail="Reminder not found")


# ---------------------------------------------------------------------------
# Vet contacts
# ---------------------------------------------------------------------------


@petcare_router.get("/vets", response_model=list[schemas.VetOut])
def list_vets(current_user: dict = Depends(get_current_user)):
    """List vet contacts (owner-isolated)."""
    user_id = str(current_user["id"])
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM vet_contacts WHERE user_id = ? ORDER BY emergency DESC, name",
            (user_id,),
        )
    ]


@petcare_router.post("/vets", response_model=schemas.VetOut, status_code=201)
def create_vet(
    payload: schemas.VetCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a vet contact (owner-isolated)."""
    user_id = str(current_user["id"])
    _id = execute(
        "INSERT INTO vet_contacts (user_id, name, phone, address, specialty, hours, emergency) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            user_id,
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
def delete_vet(vet_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a vet contact (owner-isolated)."""
    user_id = str(current_user["id"])
    if not delete_row("DELETE FROM vet_contacts WHERE id = ? AND user_id = ?", (vet_id, user_id)):
        raise HTTPException(status_code=404, detail="Vet contact not found")


# ---------------------------------------------------------------------------
# Conversations (chat sessions)
# ---------------------------------------------------------------------------


@petcare_router.get("/conversations", response_model=list[schemas.ConversationOut])
def list_conversations(
    pet_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List conversations for the authenticated user, optionally filtered by pet."""
    user_id = str(current_user["id"])
    if pet_id:
        _get_pet_or_404(pet_id, user_id)
        rows = query_all(
            "SELECT * FROM conversations WHERE user_id = ? AND pet_id = ? ORDER BY updated_at DESC",
            (user_id, pet_id),
        )
    else:
        rows = query_all(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
    return [dict(r) for r in rows]


@petcare_router.post("/conversations", response_model=schemas.ConversationOut, status_code=201)
def create_conversation(
    payload: schemas.ConversationCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new conversation session for a pet."""
    user_id = str(current_user["id"])
    _get_pet_or_404(payload.pet_id, user_id)
    _id = execute(
        "INSERT INTO conversations (user_id, pet_id, title) VALUES (?,?,?)",
        (user_id, payload.pet_id, payload.title or "New Conversation"),
    )
    return dict(query_one("SELECT * FROM conversations WHERE id = ?", (_id,)))


@petcare_router.get("/conversations/{conversation_id}", response_model=schemas.ConversationOut)
def get_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Get a single conversation (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return dict(row)


@petcare_router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Delete a conversation and all its messages (owner-isolated)."""
    user_id = str(current_user["id"])
    delete_row("DELETE FROM messages WHERE conversation_id = ? AND user_id = ?", (conversation_id, user_id))
    if not delete_row("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)):
        raise HTTPException(status_code=404, detail="Conversation not found")


@petcare_router.patch("/conversations/{conversation_id}", response_model=schemas.ConversationOut)
def rename_conversation(
    conversation_id: int,
    payload: schemas.ConversationRename,
    current_user: dict = Depends(get_current_user),
):
    """Rename a conversation (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one(
        "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    execute(
        "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?",
        (payload.title, conversation_id),
    )
    return dict(query_one("SELECT * FROM conversations WHERE id = ?", (conversation_id,)))


# ---------------------------------------------------------------------------
# Messages (chat messages)
# ---------------------------------------------------------------------------


@petcare_router.get("/conversations/{conversation_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List messages in a conversation with pagination (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [
        dict(r)
        for r in query_all(
            "SELECT * FROM messages WHERE conversation_id = ? AND user_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
            (conversation_id, user_id, limit, offset),
        )
    ]


@petcare_router.post("/conversations/{conversation_id}/messages", response_model=schemas.MessageOut, status_code=201)
def create_message(
    conversation_id: int,
    payload: schemas.MessageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a message in a conversation (owner-isolated)."""
    user_id = str(current_user["id"])
    row = query_one("SELECT id, pet_id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    pet_id = row["pet_id"]
    _id = execute(
        "INSERT INTO messages (conversation_id, user_id, role, content) VALUES (?,?,?,?)",
        (conversation_id, user_id, payload.role, payload.content),
    )
    execute("UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (conversation_id,))
    return dict(query_one("SELECT * FROM messages WHERE id = ?", (_id,)))


# ---------------------------------------------------------------------------
# Voice conversions
# ---------------------------------------------------------------------------


@petcare_router.get("/voice-conversions", response_model=list[schemas.VoiceConversionOut])
def list_voice_conversions(
    pet_id: Optional[int] = Query(None),
    conversation_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """List voice conversion events for the authenticated user."""
    user_id = str(current_user["id"])
    if pet_id:
        _get_pet_or_404(pet_id, user_id)
        rows = query_all(
            "SELECT * FROM voice_conversions WHERE user_id = ? AND pet_id = ? ORDER BY created_at DESC",
            (user_id, pet_id),
        )
    elif conversation_id:
        row = query_one(
            "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        rows = query_all(
            "SELECT * FROM voice_conversions WHERE user_id = ? AND conversation_id = ? ORDER BY created_at DESC",
            (user_id, conversation_id),
        )
    else:
        rows = query_all(
            "SELECT * FROM voice_conversions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
    return [dict(r) for r in rows]


@petcare_router.post("/expert/advice")
def expert_advice(
    payload: schemas.ExpertAsk,
    current_user: dict = Depends(get_current_user),
):
    """Rule-based pet care expert — answers a question with triage + advice."""
    user_id = str(current_user["id"])
    pet = _get_pet_or_404(payload.pet_id, user_id) if payload.pet_id else None
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
def expert_chat(
    payload: schemas.ExpertAsk,
    current_user: dict = Depends(get_current_user),
):
    """Non-streaming expert chat reply."""
    user_id = str(current_user["id"])
    pet = _get_pet_or_404(payload.pet_id, user_id) if payload.pet_id else None
    result = expert_engine.answer_question(payload.question, pet=pet)
    return {
        "conversation_id": payload.conversation_id,
        "pet": {"id": pet["id"], "name": pet["name"]} if pet else None,
        "reply": result["answer"],
        "triage": result["triage"],
        "topics": result["topics"],
        "disclaimer": result["disclaimer"],
    }


@petcare_router.post("/expert/chat/stream")
def expert_chat_stream(
    payload: schemas.ExpertAsk,
    current_user: dict = Depends(get_current_user),
):
    """SSE streaming chat reply — token-by-token deltas then a done event."""
    user_id = str(current_user["id"])
    pet = _get_pet_or_404(payload.pet_id, user_id) if payload.pet_id else None
    result = expert_engine.answer_question(payload.question, pet=pet)
    text = result["answer"]

    async def gen():
        for i in range(0, len(text), 4):
            chunk = {"type": "token", "content": text[i : i + 4]}
            yield f"data: {json.dumps(chunk)}\n\n"
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
# GPS Location Tracking
# ---------------------------------------------------------------------------


@petcare_router.post("/locations")
def log_location(
    latitude: float = Query(...),
    longitude: float = Query(...),
    accuracy: float = Query(0),
    altitude: Optional[float] = Query(None),
    speed: Optional[float] = Query(None),
    heading: Optional[float] = Query(None),
    provider: str = Query("unknown"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Log a GPS location point for the current user's pet."""
    user_id = str(current_user["id"])
    # Use the first pet if multiple exist; in production would be per-pet selection
    pet_row = query_one("SELECT id FROM pets WHERE user_id = ? ORDER BY name LIMIT 1", (user_id,))
    if pet_row is None:
        raise HTTPException(status_code=404, detail="No pet found for user")
    pet_id = pet_row["id"]
    execute(
        "INSERT INTO locations (user_id, pet_id, latitude, longitude, accuracy, altitude, speed, heading, provider, is_simulator) "
        "VALUES (?,?,?,?,?,?,?,?,?,0)",
        (user_id, pet_id, latitude, longitude, accuracy, altitude, speed, heading, provider),
    )
    return {"status": "logged", "pet_id": pet_id, "latitude": latitude, "longitude": longitude}


@petcare_router.get("/locations")
def list_locations(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List recent GPS location logs for the authenticated user."""
    user_id = str(current_user["id"])
    rows = query_all(
        "SELECT * FROM locations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    )
    return [dict(r) for r in rows]


@petcare_router.get("/locations/geofence")
def check_geofence(current_user: dict = Depends(get_current_user)) -> dict:
    """Check if the pet's current location is outside a geofence boundary.

    Returns status and advisory. In production, this would check against
    registered geofence zones (yards, prohibited areas, etc.).
    """
    user_id = str(current_user["id"])
    # Get the most recent location
    row = query_one(
        "SELECT * FROM locations WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
        (user_id,),
    )
    if row is None:
        return {"in_geofence": True, "advisory": "No location data available"}

    # Simple geofence check: if accuracy is too high (simulator-like) or
    # coordinates indicate a known simulator pattern, flag it
    lat = row["latitude"]
    lon = row["longitude"]
    acc = row["accuracy"]

    # Simulator exclusion: high accuracy variance or known simulator patterns
    is_simulator_flag = row["is_simulator"] or (acc > 100 and lat in (-74, 74) and lon in (-180, 180))

    advisory = ""
    if is_simulator_flag:
        advisory = ("Simulator location detected - ignoring for production safety. "
                    "Use the mobile app for real GPS data.")

    return {
        "in_geofence": not is_simulator_flag,
        "current_location": {"latitude": lat, "longitude": lon},
        "accuracy": acc,
        "is_simulator": bool(is_simulator_flag),
        "advisory": advisory,
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@petcare_router.get("/dashboard")
def dashboard(current_user: dict = Depends(get_current_user)):
    """Aggregate overview: pets, due vaccines, due care tasks, emergency vets."""
    user_id = str(current_user["id"])
    pets = [_with_age(p) for p in query_all("SELECT * FROM pets WHERE user_id = ? ORDER BY name", (user_id,))]
    due_vax = []
    due_care = []

    for p in pets:
        triage_vax = expert_engine.vaccination_summary(
            [
                dict(r)
                for r in query_all(
                    "SELECT * FROM vaccination_records WHERE pet_id = ? AND user_id = ?",
                    (p["id"], user_id),
                )
            ]
        )
        due_vax.extend(triage_vax.get("overdue", []))
        due_vax.extend(triage_vax.get("upcoming", []))

        for c in query_all(
            "SELECT * FROM care_schedules WHERE pet_id = ? AND user_id = ? AND active = 1",
            (p["id"], user_id),
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
                "SELECT * FROM vet_contacts WHERE user_id = ? AND emergency = 1 ORDER BY name",
                (user_id,),
            )
        ],
    }