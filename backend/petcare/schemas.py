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
