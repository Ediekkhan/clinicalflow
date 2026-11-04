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


class PatientRegistry(Base):
    __tablename__ = "patient_registry"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_patient_registry_account"),
        UniqueConstraint(
            "internal_identifier", name="uq_patient_registry_internal_identifier"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    internal_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(128), nullable=False, default="NG")
    national_identifier_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sex_at_birth: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender_identity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    address_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String(32), nullable=False, default="en"
    )
    duplicate_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    duplicate_review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="CLEAR"
    )
    is_deceased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deceased_at: Mapped[datetime | None] = mapped_column(
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


class PatientFacilityIdentity(Base):
    __tablename__ = "patient_facility_identities"
    __table_args__ = (
        UniqueConstraint(
            "patient_id", "facility_id", name="uq_patient_facility_identity"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patient_registry.id"),
        nullable=False,
        index=True,
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    local_card_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ProviderRegistry(Base):
    __tablename__ = "provider_registry"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_provider_registry_account"),
        Index("ix_provider_registry_licence", "licence_jurisdiction", "licence_number"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    practitioner_identifier: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    professional_role: Mapped[str] = mapped_column(String(64), nullable=False)
    licence_jurisdiction: Mapped[str | None] = mapped_column(String(128), nullable=True)
    licence_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    specialty_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("specialties.id"), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class FacilityRegistry(Base):
    __tablename__ = "facility_registry"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_facility_registry_tenant"),
        Index(
            "ix_facility_registry_search",
            "facility_type",
            "country",
            "status",
            "accepts_patients",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="HOSPITAL"
    )
    country: Mapped[str] = mapped_column(String(128), nullable=False, default="NG")
    jurisdiction: Mapped[str | None] = mapped_column(String(128), nullable=True)
    opening_hours_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_capable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    equipment_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    age_groups_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="AVAILABLE"
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    accepts_patients: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class FacilityService(Base):
    __tablename__ = "facility_services"
    __table_args__ = (
        UniqueConstraint(
            "facility_registry_id",
            "service_code",
            "specialty_code",
            name="uq_facility_service_capability",
        ),
        Index(
            "ix_facility_services_search", "service_code", "specialty_code", "status"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    facility_registry_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("facility_registry.id"), nullable=False
    )
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    specialty_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    available_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PayerPlanRegistry(Base):
    __tablename__ = "payer_plan_registry"
    __table_args__ = (UniqueConstraint("code", name="uq_payer_plan_registry_code"),)
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    country: Mapped[str] = mapped_column(String(128), nullable=False, default="NG")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
