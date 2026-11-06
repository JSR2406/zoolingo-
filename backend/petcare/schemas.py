"""FastAPI schemas (Pydantic v2) for the PetCare platform."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------


class PetBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    species: str = "dog"
    breed: str = ""
    gender: str = "unknown"
    date_of_birth: Optional[dt.date] = None
    weight_kg: float = 0.0
    microchip_id: str = ""
    avatar_emoji: str = "🐾"
    notes: str = ""


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    breed: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[dt.date] = None
    weight_kg: Optional[float] = None
    microchip_id: Optional[str] = None
    avatar_emoji: Optional[str] = None
    notes: Optional[str] = None


class PetOut(PetBase):
    id: int
    age_years: Optional[float] = None
    created_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Vaccinations
# ---------------------------------------------------------------------------


class VaccinationBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    administered_on: Optional[dt.date] = None
    next_due_on: Optional[dt.date] = None
    administered_at: str = ""
    notes: str = ""


class VaccinationCreate(VaccinationBase):
    pass


class VaccinationOut(VaccinationBase):
    id: int
    pet_id: int
    status: str = "up-to-date"

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Weight logs
# ---------------------------------------------------------------------------


class WeightCreate(BaseModel):
    weight_kg: float = Field(gt=0, le=500)
    logged_on: Optional[dt.date] = None


class WeightOut(WeightCreate):
    id: int
    pet_id: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Health records
# ---------------------------------------------------------------------------


class HealthRecordBase(BaseModel):
    record_type: str = "note"
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    recorded_on: Optional[dt.date] = None


class HealthRecordCreate(HealthRecordBase):
    pass


class HealthRecordOut(HealthRecordBase):
    id: int
    pet_id: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Care schedules
# ---------------------------------------------------------------------------


class CareScheduleBase(BaseModel):
    task: str = Field(min_length=1, max_length=200)
    category: str = "care"
    frequency: str = "daily"
    time_of_day: str = ""
    next_due_on: Optional[dt.date] = None
    active: bool = True


class CareScheduleCreate(CareScheduleBase):
    pass


class CareScheduleUpdate(BaseModel):
    task: Optional[str] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    time_of_day: Optional[str] = None
    next_due_on: Optional[dt.date] = None
    active: Optional[bool] = None


class CareScheduleOut(CareScheduleBase):
    id: int
    pet_id: int
    status: str = "upcoming"

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Medication schedules
# ---------------------------------------------------------------------------


class MedicationScheduleBase(BaseModel):
    pet_id: int
    medication_name: str = Field(min_length=1, max_length=200)
    dosage: str = ""
    frequency: str = "daily"
    time_of_day: str = ""
    next_due_on: Optional[dt.date] = None
    active: bool = True


class MedicationScheduleCreate(MedicationScheduleBase):
    pass


class MedicationScheduleUpdate(BaseModel):
    medication_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    time_of_day: Optional[str] = None
    next_due_on: Optional[dt.date] = None
    active: Optional[bool] = None


class MedicationScheduleOut(MedicationScheduleBase):
    id: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


class ReminderBase(BaseModel):
    pet_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    kind: str = "medication"
    target_date: Optional[dt.date] = None
    delivered_at: str = ""
    delivery_method: str = "app"
    status: str = "pending"


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    target_date: Optional[dt.date] = None
    delivered_at: Optional[str] = None
    delivery_method: Optional[str] = None
    status: Optional[str] = None


class ReminderOut(ReminderBase):
    id: int
    user_id: str
    medication_schedule_id: Optional[int] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Vet contacts
# ---------------------------------------------------------------------------


class VetBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = ""
    address: str = ""
    specialty: str = "general"
    hours: str = ""
    emergency: bool = False


class VetCreate(VetBase):
    pass


class VetOut(VetBase):
    id: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Expert
# ---------------------------------------------------------------------------


class ExpertAsk(BaseModel):
    pet_id: Optional[int] = None
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class ConversationBase(BaseModel):
    pet_id: int
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    pass


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ConversationOut(ConversationBase):
    id: int
    user_id: str
    title: str
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class MessageBase(BaseModel):
    conversation_id: int
    role: str = Field(min_length=1, max_length=20)  # 'user' or 'assistant'
    content: str = Field(min_length=1, max_length=5000)


class MessageCreate(MessageBase):
    pass


class MessageOut(MessageBase):
    id: int
    user_id: str
    created_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Voice conversions
# ---------------------------------------------------------------------------


class VoiceConversionBase(BaseModel):
    pet_id: Optional[int] = None
    conversation_id: Optional[int] = None
    animal: str
    emotion: str
    interpretation: str
    interpretation_score: Optional[float] = None
    language: str = "en-IN"
    status: str = "success"


class VoiceConversionCreate(VoiceConversionBase):
    pass


class VoiceConversionOut(VoiceConversionBase):
    id: int
    user_id: str
    created_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True
