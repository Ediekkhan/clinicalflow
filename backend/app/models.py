from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4, UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state_location: Mapped[str] = mapped_column(String(64), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    accepts_patients: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="tenant", foreign_keys="Ticket.tenant_id")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="tenant")


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    hashed_pin: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthAccount(Base):
    __tablename__ = "auth_accounts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    card_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lga: Mapped[str | None] = mapped_column(String(128), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hmo_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(8), nullable=True)
    genotype: Mapped[str | None] = mapped_column(String(8), nullable=True)
    known_allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False, index=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    selected_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=True, index=True)
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_tenant_queue", "tenant_id", "queue_status"),
        Index("ix_tickets_tenant_phone", "tenant_id", "customer_phone"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    ticket_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_intake_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_group_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="WEB")
    urgency_level: Mapped[str] = mapped_column(String(32), nullable=False, default="ROUTINE")
    matched_condition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assigned_specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    queue_status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    is_manually_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    appointment_slot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    patient_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    routed_tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    route_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    assigned_specialist_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    tenant: Mapped[Tenant] = relationship(back_populates="tickets", foreign_keys=[tenant_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_tenant_timestamp", "tenant_id", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    staff_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff.id"), nullable=True)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False, default="SYSTEM")
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="audit_logs")


class DemoRequest(Base):
    __tablename__ = "demo_requests"
    __table_args__ = (Index("ix_demo_requests_tenant_created", "tenant_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    facility_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="WEBSITE")
    daily_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_saved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(128), nullable=False)
    doctor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True)
    room_label: Mapped[str] = mapped_column(String(64), nullable=False)
    max_daily_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ProviderSlot(Base):
    __tablename__ = "provider_slots"
    __table_args__ = (
        Index("ix_provider_slots_tenant_start", "tenant_id", "starts_at"),
        Index("ix_provider_slots_provider_start", "provider_id", "starts_at", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    provider_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("providers.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lock_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_booked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class HospitalDoctorMembership(Base):
    __tablename__ = "hospital_doctor_memberships"
    __table_args__ = (
        UniqueConstraint("hospital_id", "doctor_id", "specialty_id", name="uq_hospital_doctor_specialty"),
        Index("ix_hospital_doctor_memberships_hospital_specialty", "hospital_id", "specialty_id"),
        Index("ix_hospital_doctor_memberships_doctor", "doctor_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    doctor_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    specialty_id: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    employment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    notification_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class HospitalDepartment(Base):
    __tablename__ = "hospital_departments"
    __table_args__ = (
        UniqueConstraint("hospital_id", "code", name="uq_hospital_department_code"),
        Index("ix_hospital_departments_hospital_status", "hospital_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    coordinator_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class ProviderAvailability(Base):
    __tablename__ = "provider_availability"
    __table_args__ = (
        Index("ix_provider_availability_membership_start", "membership_id", "starts_at"),
        Index("ix_provider_availability_hospital_department", "hospital_id", "department_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    maximum_appointments: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    booked_appointments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class StaffMembership(Base):
    __tablename__ = "staff_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "hospital_id", "department_id", "role", name="uq_staff_membership_workspace_role"),
        Index("ix_staff_memberships_user", "user_id"),
        Index("ix_staff_memberships_hospital_department", "hospital_id", "department_id"),
        Index("ix_staff_memberships_assignment", "hospital_id", "department_id", "specialty_id", "role"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    specialty_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    professional_license_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    employment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    notification_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_on_duty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    daily_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    active_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    active_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class StaffInvitation(Base):
    __tablename__ = "staff_invitations"
    __table_args__ = (
        UniqueConstraint("invitation_code", name="uq_staff_invitations_code"),
        Index("ix_staff_invitations_hospital_department", "hospital_id", "department_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    permitted_role: Mapped[str] = mapped_column(String(32), nullable=False)
    invitation_code: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    invited_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invited_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intended_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    invited_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class SignupApplication(Base):
    __tablename__ = "signup_applications"
    __table_args__ = (Index("ix_signup_applications_type_status", "application_type", "status"), Index("ix_signup_applications_email", "email"), Index("ix_signup_applications_phone", "phone"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    application_type: Mapped[str] = mapped_column(String(32), nullable=False)
    onboarding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="DRAFT")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invitation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_invitations.id"), nullable=True)
    account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    consent_version: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class OrganizationApplication(Base):
    __tablename__ = "organization_applications"
    __table_args__ = (Index("ix_organization_applications_status", "verification_status"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False, unique=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    licence_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    regulatory_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False, default="PENDING_VERIFICATION")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ProfessionalCredential(Base):
    __tablename__ = "professional_credentials"
    __table_args__ = (UniqueConstraint("licence_number", "jurisdiction", name="uq_professional_credential_jurisdiction"), Index("ix_professional_credentials_application", "signup_application_id"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False)
    licence_number: Mapped[str] = mapped_column(String(128), nullable=False)
    licensing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(128), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False, default="PENDING_VERIFICATION")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class VerificationDocument(Base):
    __tablename__ = "verification_documents"
    __table_args__ = (Index("ix_verification_documents_application", "signup_application_id"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    private_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False, default="PENDING_VERIFICATION")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ConsentRecord(Base):
    __tablename__ = "consent_records"
    __table_args__ = (Index("ix_consent_records_application", "signup_application_id"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ApplicationReviewHistory(Base):
    __tablename__ = "application_review_history"
    __table_args__ = (Index("ix_application_review_history_application", "signup_application_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False)
    reviewer_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class VerificationEvent(Base):
    __tablename__ = "verification_events"
    __table_args__ = (Index("ix_verification_events_application_type", "signup_application_id", "event_type"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_tenant_status", "tenant_id", "status"),
        Index("ix_appointments_ticket", "ticket_id"),
        Index("ix_appointments_hospital_doctor", "hospital_id", "doctor_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    department_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    doctor_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True)
    staff_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=True, index=True)
    specialty_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    slot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("provider_slots.id"), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    urgency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="BOOKED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class ClientMutation(Base):
    __tablename__ = "client_mutations"
    __table_args__ = (
        Index("ix_client_mutations_tenant_key", "tenant_id", "idempotency_key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ConsultationNote(Base):
    __tablename__ = "consultation_notes"
    __table_args__ = (Index("ix_consultation_notes_tenant_ticket", "tenant_id", "ticket_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    specialist_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class SpecialistMessage(Base):
    __tablename__ = "specialist_messages"
    __table_args__ = (Index("ix_specialist_messages_tenant_specialist", "tenant_id", "specialist_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    specialist_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    sender_label: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant_recipient", "tenant_id", "recipient_account_id"),
        Index("ix_notifications_appointment", "appointment_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    recipient_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    recipient_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=True)
    hospital_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recipient_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    recipient_role: Mapped[str] = mapped_column(String(32), nullable=False)
    appointment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    ticket_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="NORMAL")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class OperationalRecord(Base):
    __tablename__ = "operational_records"
    __table_args__ = (Index("ix_operational_records_tenant_resource", "tenant_id", "entity", "resource"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    entity: Mapped[str] = mapped_column(String(32), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
