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


class PayerOrganization(Base):
    __tablename__ = "payer_organizations"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class HealthPlan(Base):
    __tablename__ = "health_plans"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    payer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class MemberCoverage(Base):
    __tablename__ = "member_coverages"
    __table_args__ = (
        UniqueConstraint("payer_id", "member_number", name="uq_payer_member_number"),
        Index("ix_member_coverage_patient", "patient_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    payer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("health_plans.id"), nullable=False
    )
    member_number: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Benefit(Base):
    __tablename__ = "benefits"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("health_plans.id"), nullable=False
    )
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    coverage_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    requires_authorization: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    annual_limit_minor: Mapped[int | None] = mapped_column(Integer)


class ProviderContract(Base):
    __tablename__ = "provider_contracts"
    __table_args__ = (
        UniqueConstraint("payer_id", "facility_id", name="uq_payer_facility_contract"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    payer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EligibilityRequest(Base):
    __tablename__ = "eligibility_requests"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    payer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id")
    )
    coverage_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("member_coverages.id")
    )
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lawful_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class EligibilityResponse(Base):
    __tablename__ = "eligibility_responses"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("eligibility_requests.id"),
        nullable=False,
        unique=True,
    )
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    patient_responsibility_minor: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PriorAuthorization(Base):
    __tablename__ = "prior_authorizations"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    coverage_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("member_coverages.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    minimum_clinical_summary: Mapped[str | None] = mapped_column(Text)
    emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"
    __table_args__ = (
        UniqueConstraint(
            "payer_id", "external_reference", name="uq_claim_payer_reference"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    payer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False
    )
    coverage_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("member_coverages.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    external_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUBMITTED")
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    lawful_basis: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ClaimItem(Base):
    __tablename__ = "claim_items"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("insurance_claims.id"), nullable=False
    )
    service_code: Mapped[str] = mapped_column(String(128), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ClaimResponse(Base):
    __tablename__ = "claim_responses"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("insurance_claims.id"),
        nullable=False,
        unique=True,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DenialReason(Base):
    __tablename__ = "denial_reasons"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    payer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class ClaimAppeal(Base):
    __tablename__ = "claim_appeals"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    claim_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("insurance_claims.id"), nullable=False
    )
    submitted_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SUBMITTED")
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Remittance(Base):
    __tablename__ = "remittances"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    payer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payer_organizations.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
