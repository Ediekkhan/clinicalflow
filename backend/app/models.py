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
    # Nullable for a safe migration: existing application accounts continue
    # to work until they are linked to a Supabase Auth user.
    supabase_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, unique=True, index=True)
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
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="NG")
    emergency_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hmo_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(8), nullable=True)
    genotype: Mapped[str | None] = mapped_column(String(8), nullable=True)
    known_allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PatientRegistry(Base):
    __tablename__ = "patient_registry"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_patient_registry_account"),
        UniqueConstraint("internal_identifier", name="uq_patient_registry_internal_identifier"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    internal_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(128), nullable=False, default="NG")
    national_identifier_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sex_at_birth: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender_identity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(32), nullable=False, default="en")
    duplicate_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    duplicate_review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="CLEAR")
    is_deceased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deceased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class PatientFacilityIdentity(Base):
    __tablename__ = "patient_facility_identities"
    __table_args__ = (UniqueConstraint("patient_id", "facility_id", name="uq_patient_facility_identity"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("patient_registry.id"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    local_card_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ProviderRegistry(Base):
    __tablename__ = "provider_registry"
    __table_args__ = (UniqueConstraint("account_id", name="uq_provider_registry_account"), Index("ix_provider_registry_licence", "licence_jurisdiction", "licence_number"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    practitioner_identifier: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    professional_role: Mapped[str] = mapped_column(String(64), nullable=False)
    licence_jurisdiction: Mapped[str | None] = mapped_column(String(128), nullable=True)
    licence_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    specialty_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("specialties.id"), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FacilityRegistry(Base):
    __tablename__ = "facility_registry"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_facility_registry_tenant"), Index("ix_facility_registry_search", "facility_type", "country", "status", "accepts_patients"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(64), nullable=False, default="HOSPITAL")
    country: Mapped[str] = mapped_column(String(128), nullable=False, default="NG")
    jurisdiction: Mapped[str | None] = mapped_column(String(128), nullable=True)
    opening_hours_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_capable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    equipment_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_groups_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    accepts_patients: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FacilityService(Base):
    __tablename__ = "facility_services"
    __table_args__ = (UniqueConstraint("facility_registry_id", "service_code", "specialty_code", name="uq_facility_service_capability"), Index("ix_facility_services_search", "service_code", "specialty_code", "status"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    facility_registry_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("facility_registry.id"), nullable=False)
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    specialty_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    available_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PayerPlanRegistry(Base):
    __tablename__ = "payer_plan_registry"
    __table_args__ = (UniqueConstraint("code", name="uq_payer_plan_registry_code"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(128), nullable=False, default="NG")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
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
    revoked_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    terminology_release_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("terminology_releases.id"), nullable=True, index=True)
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


class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    __table_args__ = (UniqueConstraint("ticket_id", name="uq_routing_decision_ticket"), Index("ix_routing_decisions_destination_created", "selected_facility_id", "created_at"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    patient_owner_tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    selected_facility_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    required_service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    required_specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    urgency: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SELECTED")
    selection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_preference_facility_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    manual_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    patient_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    selected_hospital_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cross_border: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eligibility_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_candidates: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    routing_policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="country-first-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RoutingCandidate(Base):
    __tablename__ = "routing_candidates"
    __table_args__ = (UniqueConstraint("routing_decision_id", "facility_id", name="uq_routing_candidate_facility"), Index("ix_routing_candidates_decision_rank", "routing_decision_id", "rank"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    routing_decision_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("routing_decisions.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    suitability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    has_required_capability: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_emergency_capability: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_staff_coverage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_capacity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

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



class Specialty(Base):
    __tablename__ = "specialties"
    __table_args__ = (
        UniqueConstraint("code", name="uq_specialties_code"),
        Index("ix_specialties_status_name", "status", "name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
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
    department_ref_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("hospital_departments.id"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    specialty_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    specialty_ref_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("specialties.id"), nullable=True, index=True)
    legacy_doctor_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("hospital_doctor_memberships.id"), nullable=True, unique=True)
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


class ClinicalPrivilege(Base):
    __tablename__ = "clinical_privileges"
    __table_args__ = (
        UniqueConstraint("membership_id", "code", name="uq_clinical_privilege_membership_code"),
        Index("ix_clinical_privileges_membership_status", "membership_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    granted_by_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    specialty_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
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

class PatientConsentDirective(Base):
    __tablename__ = "patient_consent_directives"
    __table_args__ = (UniqueConstraint("patient_id", "purpose", "grantee_type", "grantee_id", name="uq_patient_consent_scope"), Index("ix_patient_consent_lookup", "patient_id", "purpose", "status"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("patient_registry.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    grantee_type: Mapped[str] = mapped_column(String(32), nullable=False, default="CARE_TEAM")
    grantee_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    data_categories_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProvenanceRecord(Base):
    __tablename__ = "provenance_records"
    __table_args__ = (Index("ix_provenance_resource", "resource_type", "resource_id", "recorded_at"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class HealthCardCredential(Base):
    __tablename__ = "health_card_credentials"
    __table_args__ = (Index("ix_health_card_token_hash", "token_hash", unique=True), Index("ix_health_card_patient_status", "patient_id", "status"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("patient_registry.id"), nullable=False)
    issuer_facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    card_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emergency_access_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

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


class FacilityVerificationCase(Base):
    __tablename__ = "facility_verification_cases"
    __table_args__ = (
        UniqueConstraint("signup_application_id", name="uq_facility_verification_case_application"),
        Index("ix_facility_verification_cases_queue", "status", "review_due_at", "priority"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    signup_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False)
    organization_application_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organization_applications.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="SUBMITTED")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="STANDARD")
    assigned_reviewer_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transition_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    government_check_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    risk_flags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalRegistryCheck(Base):
    __tablename__ = "external_registry_checks"
    __table_args__ = (Index("ix_external_registry_checks_case", "verification_case_id", "checked_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    verification_case_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("facility_verification_cases.id"), nullable=False)
    registry_code: Mapped[str] = mapped_column(String(64), nullable=False)
    query_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)


class VerificationFinding(Base):
    __tablename__ = "verification_findings"
    __table_args__ = (Index("ix_verification_findings_case_status", "verification_case_id", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    verification_case_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("facility_verification_cases.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="INFO")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    resolved_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FacilityAdminActivation(Base):
    __tablename__ = "facility_admin_activations"
    __table_args__ = (Index("ix_facility_admin_activations_token", "token_hash", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    verification_case_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("facility_verification_cases.id"), nullable=False)
    account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (Index("ix_notification_deliveries_retry", "status", "next_attempt_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class AppointmentAssignmentRequest(Base):
    __tablename__ = "appointment_assignment_requests"
    __table_args__ = (UniqueConstraint("ticket_id", "recipient_membership_id", name="uq_assignment_request_ticket_membership"), Index("ix_assignment_requests_recipient_status", "recipient_user_id", "status", "expires_at"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    appointment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    recipient_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    recipient_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=True)
    specialty_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_events_delivery", "status", "available_at", "created_at"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False, default="RESTRICTED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class CareTeamAssignment(Base):
    __tablename__ = "care_team_assignments"
    __table_args__ = (
        Index("ix_care_team_assignments_ticket_user", "ticket_id", "user_id", "status"),
        Index("ix_care_team_assignments_membership", "membership_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    appointment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("appointments.id"), nullable=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False)
    assignment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    permitted_sections_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BreakGlassGrant(Base):
    __tablename__ = "break_glass_grants"
    __table_args__ = (Index("ix_break_glass_grants_ticket_membership", "ticket_id", "membership_id", "expires_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hospital_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (Index("ix_referrals_destination_status", "destination_facility_id", "status"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    origin_facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    destination_facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    ticket_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"))
    required_capability: Mapped[str] = mapped_column(String(128), nullable=False)
    required_specialty: Mapped[str] = mapped_column(String(128), nullable=False)
    urgency: Mapped[str] = mapped_column(String(32), nullable=False, default="ROUTINE")
    clinical_summary: Mapped[str | None] = mapped_column(Text)
    consent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("consent_records.id"))
    consent_withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    decision_reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_account_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class TransferRequest(Base):
    __tablename__ = "transfer_requests"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    referral_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("referrals.id"), nullable=False, unique=True)
    transport_mode: Mapped[str | None] = mapped_column(String(64))
    handoff_notes: Mapped[str | None] = mapped_column(Text)
    departing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class Encounter(Base):
    __tablename__ = "encounters"
    __table_args__ = (Index("ix_encounters_patient_facility", "patient_id", "facility_id", "status"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    appointment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("appointments.id"))
    referral_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("referrals.id"))
    assigned_clinician_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    encounter_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="IN_PROGRESS")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class CareTeam(Base):
    __tablename__ = "care_teams"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class CareTeamMember(Base):
    __tablename__ = "care_team_members"
    __table_args__ = (UniqueConstraint("care_team_id", "membership_id", name="uq_care_team_membership"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    care_team_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("care_teams.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    author_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(64), nullable=False, default="PROGRESS")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="FINAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ConditionRecord(Base):
    __tablename__ = "condition_records"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    code: Mapped[str | None] = mapped_column(String(64))
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    clinical_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    recorded_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class AllergyRecord(Base):
    __tablename__ = "allergy_records"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    substance: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    recorded_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class MedicationHistory(Base):
    __tablename__ = "medication_history"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ProcedureRecord(Base):
    __tablename__ = "procedure_records"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64))
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    performed_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ClinicalObservation(Base):
    __tablename__ = "clinical_observations"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    abnormal_flag: Mapped[str | None] = mapped_column(String(32))
    observed_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class CarePlan(Base):
    __tablename__ = "care_plans"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goals_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    author_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ClinicalTask(Base):
    __tablename__ = "clinical_tasks"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    assignee_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ClinicalDocument(Base):
    __tablename__ = "clinical_documents"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    uploaded_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class LaboratoryOrder(Base):
    __tablename__ = "laboratory_orders"
    __table_args__ = (Index("ix_lab_orders_facility_status", "laboratory_id", "status"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    ordering_facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    laboratory_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    ordering_clinician_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    clinical_context: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="ROUTINE")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    patient_release_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="AFTER_FINAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class OrderedTest(Base):
    __tablename__ = "ordered_tests"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("laboratory_orders.id"), nullable=False)
    test_code: Mapped[str] = mapped_column(String(64), nullable=False)
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    loinc_code: Mapped[str | None] = mapped_column(String(32))
    specimen_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ORDERED")

class Specimen(Base):
    __tablename__ = "specimens"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("laboratory_orders.id"), nullable=False)
    accession_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    specimen_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXPECTED")
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collector_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Accession(Base):
    __tablename__ = "accessions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    specimen_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("specimens.id"), nullable=False, unique=True)
    accession_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    laboratory_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
class SpecimenCollection(Base):
    __tablename__ = "specimen_collections"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    specimen_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("specimens.id"), nullable=False)
    collector_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    collection_site: Mapped[str | None] = mapped_column(String(128))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

class SpecimenCustodyEvent(Base):
    __tablename__ = "specimen_custody_events"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    specimen_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("specimens.id"), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class LaboratoryResult(Base):
    __tablename__ = "laboratory_results"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ordered_test_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("ordered_tests.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    reference_range: Mapped[str | None] = mapped_column(String(128))
    interpretation: Mapped[str | None] = mapped_column(String(64))
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PRELIMINARY")
    entered_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("laboratory_orders.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PRELIMINARY")
    conclusion: Mapped[str | None] = mapped_column(Text)
    pdf_storage_key: Mapped[str | None] = mapped_column(String(512))
    reviewed_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_to_patient_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class QualityControlReview(Base):
    __tablename__ = "quality_control_reviews"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("diagnostic_reports.id"), nullable=False)
    reviewer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ResultCorrection(Base):
    __tablename__ = "result_corrections"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    result_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("laboratory_results.id"), nullable=False)
    previous_value: Mapped[str] = mapped_column(String(255), nullable=False)
    corrected_value: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class CriticalResultAcknowledgement(Base):
    __tablename__ = "critical_result_acknowledgements"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    result_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("laboratory_results.id"), nullable=False, unique=True)
    clinician_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    action_taken: Mapped[str | None] = mapped_column(Text)

class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (UniqueConstraint("country_code", "code", name="uq_medication_country_code"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    form: Mapped[str | None] = mapped_column(String(64))
    strength: Mapped[str | None] = mapped_column(String(64))
    controlled_schedule: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class Prescription(Base):
    __tablename__ = "prescriptions"
    __table_args__ = (Index("ix_prescriptions_patient_status", "patient_id", "status"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    encounter_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("encounters.id"))
    prescriber_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    prescriber_membership_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    pharmacy_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="NG")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SIGNED")
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    prescription_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False)
    medication_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("medications.id"), nullable=False)
    dosage: Mapped[str] = mapped_column(String(255), nullable=False)
    route: Mapped[str | None] = mapped_column(String(64))
    frequency: Mapped[str] = mapped_column(String(128), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_dispensed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    substitution_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")

class PharmacyOrder(Base):
    __tablename__ = "pharmacy_orders"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    prescription_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False, unique=True)
    pharmacy_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RECEIVED")
    validated_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    validation_notes: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("pharmacy_id", "medication_id", "batch_number", name="uq_inventory_medication_batch"), Index("ix_inventory_expiry", "pharmacy_id", "expires_at"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    pharmacy_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    medication_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("medications.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")

class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    actor_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class DispenseEvent(Base):
    __tablename__ = "dispense_events"
    __table_args__ = (UniqueConstraint("prescription_item_id", "idempotency_key", name="uq_dispense_item_idempotency"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    pharmacy_order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("pharmacy_orders.id"), nullable=False)
    prescription_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("prescription_items.id"), nullable=False)
    inventory_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dispenser_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    dispensed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class SubstitutionRequest(Base):
    __tablename__ = "substitution_requests"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    prescription_item_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("prescription_items.id"), nullable=False)
    proposed_medication_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("medications.id"), nullable=False)
    requested_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    decided_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class InteractionAlert(Base):
    __tablename__ = "interaction_alerts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    prescription_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ControlledMedicationLog(Base):
    __tablename__ = "controlled_medication_logs"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dispense_event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dispense_events.id"), nullable=False, unique=True)
    schedule: Mapped[str] = mapped_column(String(32), nullable=False)
    witness_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    register_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class PharmacyDelivery(Base):
    __tablename__ = "pharmacy_deliveries"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    pharmacy_order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("pharmacy_orders.id"), nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PICKUP")
    masked_destination: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class PatientCounselling(Base):
    __tablename__ = "patient_counselling"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    pharmacy_order_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("pharmacy_orders.id"), nullable=False)
    pharmacist_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    topics_json: Mapped[str] = mapped_column(Text, nullable=False)
    patient_understood: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    counselled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class PayerOrganization(Base):
    __tablename__ = "payer_organizations"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class HealthPlan(Base):
    __tablename__ = "health_plans"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class MemberCoverage(Base):
    __tablename__ = "member_coverages"
    __table_args__ = (UniqueConstraint("payer_id", "member_number", name="uq_payer_member_number"), Index("ix_member_coverage_patient", "patient_id", "status"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    payer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False)
    plan_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("health_plans.id"), nullable=False)
    member_number: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Benefit(Base):
    __tablename__ = "benefits"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("health_plans.id"), nullable=False)
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    coverage_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    annual_limit_minor: Mapped[int | None] = mapped_column(Integer)

class ProviderContract(Base):
    __tablename__ = "provider_contracts"
    __table_args__ = (UniqueConstraint("payer_id", "facility_id", name="uq_payer_facility_contract"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class EligibilityRequest(Base):
    __tablename__ = "eligibility_requests"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    payer_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"))
    coverage_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_coverages.id"))
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lawful_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class EligibilityResponse(Base):
    __tablename__ = "eligibility_responses"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("eligibility_requests.id"), nullable=False, unique=True)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    patient_responsibility_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class PriorAuthorization(Base):
    __tablename__ = "prior_authorizations"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    coverage_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_coverages.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    minimum_clinical_summary: Mapped[str | None] = mapped_column(Text)
    emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    __table_args__ = (UniqueConstraint("payer_id", "external_reference", name="uq_claim_payer_reference"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False)
    coverage_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("member_coverages.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUBMITTED")
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    lawful_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class ClaimItem(Base):
    __tablename__ = "claim_items"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("insurance_claims.id"), nullable=False)
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class ClaimResponse(Base):
    __tablename__ = "claim_responses"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("insurance_claims.id"), nullable=False, unique=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class DenialReason(Base):
    __tablename__ = "denial_reasons"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class ClaimAppeal(Base):
    __tablename__ = "claim_appeals"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("insurance_claims.id"), nullable=False)
    submitted_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUBMITTED")
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class Remittance(Base):
    __tablename__ = "remittances"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class PaymentReconciliation(Base):
    __tablename__ = "payment_reconciliations"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    remittance_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("remittances.id"), nullable=False)
    claim_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("insurance_claims.id"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="MATCHED")
    reconciled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class GovernmentAuthority(Base):
    __tablename__ = "government_authorities"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_level: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class GovernmentUserScope(Base):
    __tablename__ = "government_user_scopes"
    __table_args__ = (UniqueConstraint("user_id", "jurisdiction_code", name="uq_government_user_jurisdiction"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    authority_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("government_authorities.id"), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    geographic_level: Mapped[str] = mapped_column(String(32), nullable=False)
    identifiable_reporting_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class MandatoryDiseaseReport(Base):
    __tablename__ = "mandatory_disease_reports"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    report_type: Mapped[str] = mapped_column(String(128), nullable=False)
    condition_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    identifiable_payload_json: Mapped[str | None] = mapped_column(Text)
    legal_authority_reference: Mapped[str | None] = mapped_column(String(255))
    submitted_by_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class SurveillanceAggregate(Base):
    __tablename__ = "surveillance_aggregates"
    __table_args__ = (UniqueConstraint("jurisdiction_code", "indicator_code", "period", name="uq_surveillance_indicator_period"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    suppression_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class NationalIndicator(Base):
    __tablename__ = "national_indicators"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class OutbreakAlert(Base):
    __tablename__ = "outbreak_alerts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class DataDisclosure(Base):
    __tablename__ = "data_disclosures"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    government_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    report_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("mandatory_disease_reports.id"))
    disclosure_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(255), nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    disclosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class SupportAccessRequest(Base):
    __tablename__ = "support_access_requests"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    requester_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    sensitive_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class SupportAccessApproval(Base):
    __tablename__ = "support_access_approvals"
    __table_args__ = (UniqueConstraint("request_id", "approver_id", name="uq_support_request_approver"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("support_access_requests.id"), nullable=False)
    approver_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class CountryPack(Base):
    __tablename__ = "country_packs"
    __table_args__ = (UniqueConstraint("country_code", "version", name="uq_country_pack_version"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    requires_legal_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class InteroperabilityMapping(Base):
    __tablename__ = "interoperability_mappings"
    __table_args__ = (UniqueConstraint("country_pack_id", "resource_type", "version", name="uq_interop_mapping_version"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    country_pack_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("country_packs.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    standard: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

class OfflineClinicalMutation(Base):
    __tablename__ = "offline_clinical_mutations"
    __table_args__ = (UniqueConstraint("account_id", "client_mutation_id", name="uq_offline_account_mutation"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    client_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mutation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class TerminologyRelease(Base):
    __tablename__ = "terminology_releases"
    __table_args__ = (UniqueConstraint("code_system", "version", "language", name="uq_terminology_release_version"), Index("ix_terminology_releases_status_system", "status", "code_system"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code_system: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    license_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

class ClinicalConcept(Base):
    __tablename__ = "clinical_concepts"
    __table_args__ = (UniqueConstraint("release_id", "code_system", "external_code", name="uq_clinical_concept_release_code"), Index("ix_clinical_concepts_search", "concept_type", "active", "preferred_name"), Index("ix_clinical_concepts_external_code", "code_system", "external_code"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    release_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("terminology_releases.id"), nullable=False)
    code_system: Mapped[str] = mapped_column(String(128), nullable=False)
    external_code: Mapped[str] = mapped_column(String(128), nullable=False)
    concept_type: Mapped[str] = mapped_column(String(32), nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(512), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text)
    parent_concept_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

class ConceptDesignation(Base):
    __tablename__ = "concept_designations"
    __table_args__ = (UniqueConstraint("concept_id", "language_code", "country_code", "normalized_term", "term_type", name="uq_concept_designation_term"), Index("ix_concept_designations_search", "normalized_term", "language_code", "country_code"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"), nullable=False)
    language_code: Mapped[str] = mapped_column(String(16), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    term: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_term: Mapped[str] = mapped_column(String(512), nullable=False)
    term_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

class ClinicalRelationship(Base):
    __tablename__ = "clinical_relationships"
    __table_args__ = (UniqueConstraint("release_id", "source_concept_id", "relationship_type", "target_concept_id", "country_code", name="uq_clinical_relationship_release"), Index("ix_clinical_relationships_source_type", "source_concept_id", "relationship_type"), Index("ix_clinical_relationships_target_type", "target_concept_id", "relationship_type"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_concept_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_concept_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"), nullable=False)
    evidence_strength: Mapped[str | None] = mapped_column(String(32))
    frequency: Mapped[str | None] = mapped_column(String(32))
    age_group: Mapped[str | None] = mapped_column(String(32))
    sex_applicability: Mapped[str | None] = mapped_column(String(32))
    pregnancy_applicability: Mapped[str | None] = mapped_column(String(32))
    country_code: Mapped[str | None] = mapped_column(String(2))
    source_reference: Mapped[str | None] = mapped_column(String(1024))
    release_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("terminology_releases.id"), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

class ClinicalContentReview(Base):
    __tablename__ = "clinical_content_reviews"
    __table_args__ = (Index("ix_clinical_content_reviews_resource", "resource_type", "resource_id", "reviewed_at"),)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reviewer_account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"))
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(1024))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
class FacilityAcceptance(Base):
    __tablename__ = "facility_acceptances"
    __table_args__ = (Index("ix_facility_acceptances_ticket_created", "ticket_id", "created_at"), Index("ix_facility_acceptances_facility_status", "facility_id", "decision"))
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    actor_account_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False)
    actor_membership_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("staff_memberships.id"))
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    next_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    redirected_facility_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("tenants.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
