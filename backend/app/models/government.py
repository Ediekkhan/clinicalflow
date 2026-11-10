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


class GovernmentAuthority(Base):
    __tablename__ = "government_authorities"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    authority_level: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class GovernmentUserScope(Base):
    __tablename__ = "government_user_scopes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "jurisdiction_code", name="uq_government_user_jurisdiction"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    authority_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("government_authorities.id"), nullable=False
    )
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    geographic_level: Mapped[str] = mapped_column(String(32), nullable=False)
    identifiable_reporting_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class MandatoryDiseaseReport(Base):
    __tablename__ = "mandatory_disease_reports"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    report_type: Mapped[str] = mapped_column(String(128), nullable=False)
    condition_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reporting_period: Mapped[str] = mapped_column(String(32), nullable=False)
    aggregate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    identifiable_payload_json: Mapped[str | None] = mapped_column(Text)
    legal_authority_reference: Mapped[str | None] = mapped_column(String(255))
    submitted_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SurveillanceAggregate(Base):
    __tablename__ = "surveillance_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "jurisdiction_code",
            "indicator_code",
            "period",
            name="uq_surveillance_indicator_period",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    suppression_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class NationalIndicator(Base):
    __tablename__ = "national_indicators"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class OutbreakAlert(Base):
    __tablename__ = "outbreak_alerts"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    jurisdiction_code: Mapped[str] = mapped_column(String(64), nullable=False)
    indicator_code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DataDisclosure(Base):
    __tablename__ = "data_disclosures"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    government_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    report_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("mandatory_disease_reports.id")
    )
    disclosure_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_basis: Mapped[str] = mapped_column(String(255), nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    disclosed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
