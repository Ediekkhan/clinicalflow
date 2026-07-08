from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.validators import PhoneValidator, SymptomTextValidator

Channel = Literal["WHATSAPP", "USSD", "WEB", "SMS"]
UrgencyLevel = Literal["CRITICAL", "URGENT", "ROUTINE"]
QueueStatus = Literal["QUEUED", "BEING_SEEN", "RESOLVED"]


class TicketBase(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=32)
    account_group_phone: str | None = Field(default=None, max_length=32)
    channel: Channel = "WEB"
    raw_intake_text: str | None = None
    appointment_slot: datetime | None = None

    @field_validator("customer_phone")
    @classmethod
    def validate_customer_phone(cls, value: str) -> str:
        return PhoneValidator.validate_nigerian_phone(value)

    @field_validator("account_group_phone")
    @classmethod
    def validate_account_phone(cls, value: str | None) -> str | None:
        return PhoneValidator.validate_nigerian_phone(value) if value else value

    @field_validator("raw_intake_text")
    @classmethod
    def validate_raw_intake(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return value
        return SymptomTextValidator.validate_symptom_text(value)


class TicketCreate(TicketBase):
    symptoms: list[str] = Field(default_factory=list)
    allow_duplicate_for_shared_phone: bool = False


class TicketUpdate(BaseModel):
    queue_status: QueueStatus | None = None
    assigned_specialty: str | None = None
    appointment_slot: datetime | None = None


class TicketRead(BaseModel):
    id: UUID
    tenant_id: UUID
    ticket_number: str
    customer_phone: str
    account_group_phone: str
    channel: Channel
    urgency_level: UrgencyLevel
    matched_condition_id: str | None
    assigned_specialty: str | None
    queue_status: QueueStatus
    is_manually_escalated: bool
    appointment_slot: datetime | None
    raw_intake_text: str | None
    extracted_symptoms: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DuplicateIntentResponse(BaseModel):
    duplicate_detected: bool = True
    account_group_phone: str
    active_ticket_numbers: list[str]
    interactive_menu: dict[str, object]


class IncomingMessage(BaseModel):
    phone: str
    text: str
    channel: Channel = "WHATSAPP"
    intent: Literal["TRIAGE", "REGISTER_NEW_PATIENT", "CANCEL", "BOOK_SLOT"] = "TRIAGE"
    selected_slot_id: UUID | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return PhoneValidator.validate_nigerian_phone(value)


class ProviderSlotRead(BaseModel):
    id: UUID
    tenant_id: UUID
    provider_name: str
    specialty: str
    room_label: str
    starts_at: datetime
    ends_at: datetime
    is_locked: bool
    lock_reason: str | None

    model_config = {"from_attributes": True}


class AppointmentCreate(BaseModel):
    ticket_id: UUID
    provider_slot_id: UUID
    channel_origin: Channel = "WEB"


class AppointmentRead(BaseModel):
    id: UUID
    tenant_id: UUID
    ticket_id: UUID
    provider_slot_id: UUID
    status: Literal["BOOKED", "CANCELLED", "COMPLETED", "NO_SHOW"]
    channel_origin: Channel
    created_at: datetime

    model_config = {"from_attributes": True}


class WebSocketEvent(BaseModel):
    type: Literal[
        "ticket.created",
        "ticket.updated",
        "ticket.escalated",
        "appointment.updated",
        "system.notice",
    ]
    tenant_id: UUID
    payload: dict[str, object]
    priority: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"
