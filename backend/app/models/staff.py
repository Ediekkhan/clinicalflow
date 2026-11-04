from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    hashed_pin: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialty: Mapped[str] = mapped_column(String(128), nullable=False)
    doctor_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True
    )
    room_label: Mapped[str] = mapped_column(String(64), nullable=False)
    max_daily_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ProviderSlot(Base):
    __tablename__ = "provider_slots"
    __table_args__ = (
        Index("ix_provider_slots_tenant_start", "tenant_id", "starts_at"),
        Index(
            "ix_provider_slots_provider_start", "provider_id", "starts_at", unique=True
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    provider_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("providers.id"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lock_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_booked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class HospitalDoctorMembership(Base):
    __tablename__ = "hospital_doctor_memberships"
    __table_args__ = (
        UniqueConstraint(
            "hospital_id",
            "doctor_id",
            "specialty_id",
            name="uq_hospital_doctor_specialty",
        ),
        Index(
            "ix_hospital_doctor_memberships_hospital_specialty",
            "hospital_id",
            "specialty_id",
        ),
        Index("ix_hospital_doctor_memberships_doctor", "doctor_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    doctor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    specialty_id: Mapped[str] = mapped_column(String(128), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    employment_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE"
    )
    notification_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    active_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class HospitalDepartment(Base):
    __tablename__ = "hospital_departments"
    __table_args__ = (
        UniqueConstraint("hospital_id", "code", name="uq_hospital_department_code"),
        Index("ix_hospital_departments_hospital_status", "hospital_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    coordinator_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=True
    )
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Specialty(Base):
    __tablename__ = "specialties"
    __table_args__ = (
        UniqueConstraint("code", name="uq_specialties_code"),
        Index("ix_specialties_status_name", "status", "name"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ProviderAvailability(Base):
    __tablename__ = "provider_availability"
    __table_args__ = (
        Index(
            "ix_provider_availability_membership_start", "membership_id", "starts_at"
        ),
        Index(
            "ix_provider_availability_hospital_department",
            "hospital_id",
            "department_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    maximum_appointments: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12
    )
    booked_appointments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class StaffMembership(Base):
    __tablename__ = "staff_memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "hospital_id",
            "department_id",
            "role",
            name="uq_staff_membership_workspace_role",
        ),
        Index("ix_staff_memberships_user", "user_id"),
        Index(
            "ix_staff_memberships_hospital_department", "hospital_id", "department_id"
        ),
        Index(
            "ix_staff_memberships_assignment",
            "hospital_id",
            "department_id",
            "specialty_id",
            "role",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    department_ref_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospital_departments.id"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    specialty_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    specialty_ref_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("specialties.id"), nullable=True, index=True
    )
    legacy_doctor_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hospital_doctor_memberships.id"),
        nullable=True,
        unique=True,
    )
    professional_license_number: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    employment_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ACTIVE"
    )
    notification_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_on_duty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    daily_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    active_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    active_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ClinicalPrivilege(Base):
    __tablename__ = "clinical_privileges"
    __table_args__ = (
        UniqueConstraint(
            "membership_id", "code", name="uq_clinical_privilege_membership_code"
        ),
        Index("ix_clinical_privileges_membership_status", "membership_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    granted_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class StaffInvitation(Base):
    __tablename__ = "staff_invitations"
    __table_args__ = (
        UniqueConstraint("invitation_code", name="uq_staff_invitations_code"),
        Index(
            "ix_staff_invitations_hospital_department", "hospital_id", "department_id"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    hospital_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    department_id: Mapped[str] = mapped_column(String(128), nullable=False)
    permitted_role: Mapped[str] = mapped_column(String(32), nullable=False)
    invitation_code: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    invited_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invited_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intended_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    specialty_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    invited_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
