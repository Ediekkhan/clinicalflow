from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


UrgencyLevel = Literal["CRITICAL", "URGENT", "ROUTINE"]
QueueStatus = Literal["QUEUED", "BEING_SEEN", "RESOLVED", "CANCELLED"]


class PatientSignup(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    phone: str = Field(min_length=7, max_length=32)
    date_of_birth: date | None = None
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    password: str = Field(min_length=8)
    latitude: float | None = None
    longitude: float | None = None
    fallback_location: str | None = None


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


class SpecialistLogin(BaseModel):
    email: str
    password: str


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
