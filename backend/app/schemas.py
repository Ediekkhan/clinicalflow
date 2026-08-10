from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

Channel = Literal["WHATSAPP", "USSD", "WEB", "SMS"]
UrgencyLevel = Literal["CRITICAL", "URGENT", "ROUTINE"]
QueueStatus = Literal["ROUTED", "AWAITING_FACILITY_ACCEPTANCE", "ACCEPTED", "REJECTED", "REDIRECTED", "TRAVELLING", "ARRIVED", "CHECKED_IN", "WAITING_FOR_NURSE", "WAITING_FOR_DOCTOR", "QUEUED", "BEING_SEEN", "ADMITTED", "DISCHARGED", "TRANSFERRED", "CANCELLED", "RESOLVED", "AWAITING_CLINICAL_REVIEW", "SPECIALIST_UNAVAILABLE"]


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


class StaffMembershipResponse(BaseModel):
    id: UUID
    hospital_id: UUID
    department_id: str
    role: str
    specialty_id: str | None = None
    verification_status: str
    employment_status: str
    is_active: bool
    is_on_duty: bool


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
    country_code: str = "NG"
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
    memberships: list[StaffMembershipResponse] = Field(default_factory=list)
    selected_membership_id: str | None = None


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


class EnterpriseEnquiryCreate(BaseModel):
    organization_legal_name: str = Field(min_length=2, max_length=255)
    organization_type: str = Field(min_length=2, max_length=80)
    country: str = Field(min_length=2, max_length=128)
    operations: str = Field(default="", max_length=2000)
    contact_name: str = Field(min_length=2, max_length=255)
    job_title: str = Field(default="", max_length=128)
    official_work_email: str = Field(min_length=5, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    telephone: str = Field(default="", max_length=32)
    website: str = Field(default="", max_length=255)
    facility_count: int | None = Field(default=None, ge=1, le=1_000_000)
    staff_count: int | None = Field(default=None, ge=0, le=10_000_000)
    monthly_patient_volume: int | None = Field(default=None, ge=0, le=100_000_000)
    current_system: str = Field(default="", max_length=255)
    integrations: str = Field(default="", max_length=4000)
    dashboards: str = Field(default="", max_length=2000)
    security_requirements: str = Field(default="", max_length=4000)
    compliance_requirements: str = Field(default="", max_length=4000)
    deployment_model: str = Field(default="", max_length=128)
    preferred_pilot_date: str = Field(default="", max_length=32)
    expected_rollout_date: str = Field(default="", max_length=32)
    budget_range: str = Field(default="", max_length=128)
    additional_message: str = Field(default="", max_length=5000)
    preferred_contact_method: str = Field(default="EMAIL", max_length=32)
    preferred_meeting_date: str = Field(default="", max_length=32)
    meeting_timezone: str = Field(default="UTC", max_length=64)
    consent_to_contact: bool


class EnterpriseEnquiryUpdate(BaseModel):
    status: Literal["NEW", "CONTACTED", "QUALIFIED", "PILOT_PROPOSED", "PROPOSAL_SENT", "NEGOTIATION", "WON", "LOST", "ARCHIVED"] | None = None
    internal_notes: str | None = Field(default=None, max_length=5000)
    follow_up_at: datetime | None = None
    assigned_to_id: UUID | None = None


class RefundCreate(BaseModel):
    amount_minor: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=3, max_length=255)


class ReconciliationResolve(BaseModel):
    resolution: str = Field(min_length=3, max_length=1000)


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
    department_id: str | None = None
    ticket_id: UUID
    doctor_id: UUID | None = None
    staff_membership_id: UUID | None = None
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
class SignupApplicationCreate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    middle_name: str | None = Field(default=None, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    country: str = Field(min_length=2, max_length=128)
    region: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    confirm_password: str | None = Field(default=None, min_length=8, max_length=128)
    invitation_token: str | None = Field(default=None, min_length=8, max_length=512)
    accept_terms: bool
    accept_privacy: bool
    marketing_consent: bool = False
    consent_version: str = Field(default="2026-07", min_length=1, max_length=32)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        normalized = str(value).strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_international_phone(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        normalized = "".join(character for character in str(value).strip() if character.isdigit() or character == "+")
        if not normalized.startswith("+") or not normalized[1:].isdigit() or not 8 <= len(normalized[1:]) <= 15:
            raise ValueError("Enter a valid international phone number including country code")
        return normalized

    @model_validator(mode="after")
    def validate_security(self) -> "SignupApplicationCreate":
        if not self.accept_terms or not self.accept_privacy:
            raise ValueError("Terms of service and privacy notice must be accepted")
        if self.password is not None:
            if self.password != self.confirm_password:
                raise ValueError("Passwords do not match")
            if not any(character.isupper() for character in self.password) or not any(character.isdigit() for character in self.password):
                raise ValueError("Password must include an uppercase letter and a number")
        return self


class SignupApplicationResponse(BaseModel):
    id: UUID
    reference: str
    application_type: str
    onboarding_type: str
    status: str
    submitted_at: datetime
    login_path: str
    dashboard_path: str | None = None


class SignupVerificationRequest(BaseModel):
    application_id: UUID
    code: str = Field(min_length=4, max_length=12)


class SignupInvitationValidateRequest(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    role: Literal["specialist", "nurse", "government", "platform-admin"]
    email: str | None = Field(default=None, max_length=255)
