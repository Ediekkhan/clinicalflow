from datetime import date, datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.validators import DateOfBirthValidator, PhoneValidator, SymptomTextValidator


UrgencyLevel = Literal["CRITICAL", "URGENT", "ROUTINE"]
QueueStatus = Literal["QUEUED", "BEING_SEEN", "RESOLVED", "CANCELLED"]


class PatientSignup(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=32)
    date_of_birth: date
    gender: Literal["MALE", "FEMALE", "OTHER"]
    password: str = Field(min_length=8)
    latitude: float | None = None
    longitude: float | None = None
    fallback_location: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", value):
            raise ValueError("Name can only contain letters, spaces, hyphens, and apostrophes")
        return value.title()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return PhoneValidator.validate_nigerian_phone(value)

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: date) -> date:
        return DateOfBirthValidator.validate_dob(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", value):
            raise ValueError("Password must contain at least one number")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("Invalid latitude")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("Invalid longitude")
        return value


class PatientRead(BaseModel):
    id: UUID
    tenant_id: UUID
    full_name: str
    phone: str
    date_of_birth: date | None
    gender: str | None
    card_number: str
    latitude: float | None
    longitude: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    patient: PatientRead


class PasswordLogin(BaseModel):
    email_or_phone: str
    password: str

    @field_validator("email_or_phone")
    @classmethod
    def normalize_login(cls, value: str) -> str:
        if "@" in value:
            return value.strip().lower()
        return PhoneValidator.validate_nigerian_phone(value)


class SpecialistLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class SpecialistRead(BaseModel):
    id: UUID
    tenant_id: UUID
    full_name: str
    specialty: str
    phone: str | None
    email: str | None
    is_available: bool

    model_config = {"from_attributes": True}


class TriageAnalyzeRequest(BaseModel):
    patient_id: UUID
    symptom_text: str = Field(min_length=4)
    latitude: float | None = None
    longitude: float | None = None

    @field_validator("symptom_text")
    @classmethod
    def validate_symptom_text(cls, value: str) -> str:
        return SymptomTextValidator.validate_symptom_text(value)

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("Invalid latitude")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("Invalid longitude")
        return value


class ClinicMatch(BaseModel):
    clinic_id: UUID
    clinic_name: str
    address: str | None
    distance_km: float
    available_slots: int
    specialist_id: UUID | None
    specialist_name: str | None


class AppointmentSlotSummary(BaseModel):
    slot_start: datetime
    slot_end: datetime
    specialist_name: str
    specialty: str


class SynTicketRead(BaseModel):
    id: UUID
    tenant_id: UUID
    patient_id: UUID | None
    ticket_number: str
    symptom_description: str | None
    extracted_symptom_ids: list[str] | None
    matched_condition_id: str | None
    matched_condition_name: str | None
    assigned_specialty: str | None
    urgency_level: UrgencyLevel
    assigned_specialist_id: UUID | None
    assigned_clinic_id: UUID | None
    queue_status: QueueStatus
    is_manually_escalated: bool
    appointment_slot: datetime | None
    channel: Literal["WEB", "WHATSAPP", "SMS", "USSD"]
    created_at: datetime

    model_config = {"from_attributes": True}


class TriageAnalyzeResponse(BaseModel):
    ticket: SynTicketRead
    condition_name: str
    urgency: UrgencyLevel
    specialty: str
    nearest_clinic: ClinicMatch
    appointment_slot: AppointmentSlotSummary
    severity_message: str


class NotificationRead(BaseModel):
    id: UUID
    tenant_id: UUID
    recipient_type: Literal["SPECIALIST", "PATIENT"]
    recipient_id: UUID
    title: str
    body: str
    is_read: bool
    ticket_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
