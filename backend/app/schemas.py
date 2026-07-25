from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

Channel = Literal["WHATSAPP", "USSD", "WEB", "SMS"]
UrgencyLevel = Literal["CRITICAL", "URGENT", "ROUTINE"]
QueueStatus = Literal["QUEUED", "BEING_SEEN", "RESOLVED", "AWAITING_CLINICAL_REVIEW", "SPECIALIST_UNAVAILABLE"]


def normalize_nigerian_phone_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = "".join(character for character in str(value) if character.isdigit() or character == "+")
    if normalized.startswith("0"):
        normalized = "+234" + normalized[1:]
    elif normalized.startswith("234"):
        normalized = "+" + normalized
    if not normalized.startswith("+234") or len(normalized) != 14 or not normalized[1:].isdigit():
        raise ValueError("Enter a valid Nigerian phone number")
    return normalized


class AuthLoginRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    password: str


class PinLoginRequest(BaseModel):
    role: Literal["nurse", "admin"]
    pin: str = Field(pattern=r"^\d{4}$")


class HospitalLoginRequest(BaseModel):
    hospital_code: str = Field(min_length=3, max_length=64)
    role: Literal["doctor", "nurse", "hospital_admin"]
    password: str = Field(min_length=4, max_length=128)


class AuthProfileResponse(BaseModel):
    id: str
    role: str
    tenant_id: str
    phone: str | None = None
    email: str | None = None
    first_name: str
    last_name: str
    full_name: str
    specialty: str | None = None
    card_number: str | None = None
    subtitle: str | None = None
    date_of_birth: datetime | None = None
    gender: str | None = None
    state: str | None = None
    lga: str | None = None
    emergency_contact: str | None = None
    hmo_provider: str | None = None
    blood_group: str | None = None
    genotype: str | None = None
    known_allergies: str | None = None
    current_medications: str | None = None
    created_at: datetime | None = None
    card_valid_from: datetime | None = None
    card_valid_until: datetime | None = None
    locked_fields: list[str] = Field(default_factory=list)


class PatientProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = None
    emergency_contact: str | None = Field(default=None, max_length=32)
    hmo_provider: str | None = Field(default=None, max_length=128)
    blood_group: str | None = Field(default=None, max_length=8)
    genotype: str | None = Field(default=None, max_length=8)
    known_allergies: str | None = Field(default=None, max_length=2000)
    current_medications: str | None = Field(default=None, max_length=2000)
    gender: str | None = Field(default=None, max_length=32)
    state: str | None = Field(default=None, max_length=128)
    lga: str | None = Field(default=None, max_length=128)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        return normalize_nigerian_phone_value(value) if value else value


class PatientCardUpdate(BaseModel):
    blood_group: str | None = Field(default=None, max_length=8)
    genotype: str | None = Field(default=None, max_length=8)
    known_allergies: str | None = Field(default=None, max_length=2000)
    emergency_contact: str | None = Field(default=None, max_length=32)
    hmo_provider: str | None = Field(default=None, max_length=128)


class AuthSessionResponse(AuthProfileResponse):
    access_expires_at: datetime


class AuthRefreshResponse(BaseModel):
    ok: bool = True
    access_expires_at: datetime


class TicketCreate(BaseModel):
    customer_phone: str = Field(min_length=10, max_length=16)
    raw_intake_text: str = Field(min_length=3, max_length=4000)
    appointment_slot: datetime | None = None
    channel: Channel = "WEB"
    account_group_phone: str | None = None

    @field_validator("customer_phone", "account_group_phone", mode="before")
    @classmethod
    def normalize_nigerian_phone(cls, value: str | None) -> str | None:
        return normalize_nigerian_phone_value(value)


class ChannelIntakeRequest(BaseModel):
    customer_phone: str = Field(min_length=10, max_length=16)
    raw_intake_text: str | None = Field(default=None, max_length=4000)
    intent: Literal["CONTINUE_EXISTING", "REGISTER_NEW_PATIENT", "BOOK_APPOINTMENT", "CONFIRM_APPOINTMENT", "CANCEL_APPOINTMENT"] | None = None
    slot_id: UUID | None = None

    @field_validator("customer_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = normalize_nigerian_phone_value(value)
        assert normalized is not None
        return normalized


class ChannelMenuOption(BaseModel):
    id: str
    title: str
    description: str


class ChannelIntakeResponse(BaseModel):
    action: Literal["SHOW_IDENTITY_MENU", "CONTINUE_EXISTING", "TICKET_CREATED", "SHOW_SLOT_MENU", "APPOINTMENT_BOOKED", "APPOINTMENT_CANCELLED"]
    channel: Literal["WHATSAPP", "SMS"]
    message: str
    active_ticket_id: UUID | None = None
    account_group_phone: str | None = None
    menu: list[ChannelMenuOption] = Field(default_factory=list)
    ticket: TicketResponse | None = None


class DemoRequestCreate(BaseModel):
    organization_name: str | None = Field(default=None, max_length=255)
    work_email: str = Field(min_length=5, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    phone: str | None = Field(default=None, max_length=32)
    facility_type: str | None = Field(default=None, max_length=128)
    source: Literal["WEBSITE", "ROI_CALCULATOR"] = "WEBSITE"
    daily_capacity: int | None = Field(default=None, ge=1, le=10000)
    minutes_saved: int | None = Field(default=None, ge=1, le=120)


class DemoRequestResponse(BaseModel):
    id: UUID
    message: str


class TicketResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    ticket_number: str
    customer_phone: str
    account_group_phone: str | None = None
    channel: Channel
    urgency_level: UrgencyLevel
    matched_condition_id: str | None = None
    assigned_specialty: str | None = None
    queue_status: QueueStatus
    is_manually_escalated: bool
    appointment_slot: datetime | None = None
    patient_latitude: float | None = None
    patient_longitude: float | None = None
    routed_tenant_id: UUID | None = None
    route_distance_km: float | None = None
    created_at: datetime
    raw_intake_text: str | None = None
    extracted_symptoms: str | None = None
    version: int = 1


class TicketUpdate(BaseModel):
    queue_status: QueueStatus | None = None
    urgency_level: UrgencyLevel | None = None
    is_manually_escalated: bool | None = None
    expected_version: int | None = Field(default=None, ge=1)


class SlotResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    provider_name: str
    specialty: str
    room_label: str
    starts_at: datetime
    ends_at: datetime
    is_locked: bool
    lock_reason: str | None = None
    is_booked: bool = False


class SlotLockRequest(BaseModel):
    is_locked: bool
    reason: str | None = Field(default=None, max_length=255)


class AppointmentCreate(BaseModel):
    ticket_id: UUID
    slot_id: UUID
    customer_phone: str

    @field_validator("customer_phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = normalize_nigerian_phone_value(value)
        assert normalized is not None
        return normalized


class AppointmentMoveRequest(BaseModel):
    slot_id: UUID


class AppointmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    hospital_id: UUID
    ticket_id: UUID
    doctor_id: UUID | None = None
    specialty_id: str | None = None
    slot_id: UUID
    customer_phone: str
    urgency: str | None = None
    status: Literal["BOOKED", "CANCELLED", "COMPLETED", "AWAITING_CLINICAL_REVIEW", "SPECIALIST_UNAVAILABLE"]
    provider_name: str
    specialty: str
    room_label: str
    starts_at: datetime
    ends_at: datetime
