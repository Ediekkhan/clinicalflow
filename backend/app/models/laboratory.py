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


class LaboratoryOrder(Base):
    __tablename__ = "laboratory_orders"
    __table_args__ = (
        Index("ix_lab_orders_facility_status", "laboratory_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    ordering_facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    laboratory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    encounter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("encounters.id")
    )
    ordering_clinician_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    clinical_context: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="ROUTINE")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    patient_release_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="AFTER_FINAL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class OrderedTest(Base):
    __tablename__ = "ordered_tests"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("laboratory_orders.id"), nullable=False
    )
    test_code: Mapped[str] = mapped_column(String(64), nullable=False)
    display: Mapped[str] = mapped_column(String(255), nullable=False)
    loinc_code: Mapped[str | None] = mapped_column(String(32))
    specimen_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ORDERED")


class Specimen(Base):
    __tablename__ = "specimens"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("laboratory_orders.id"), nullable=False
    )
    accession_number: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    specimen_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EXPECTED")
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collector_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id")
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Accession(Base):
    __tablename__ = "accessions"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    specimen_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("specimens.id"), nullable=False, unique=True
    )
    accession_number: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    laboratory_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    created_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SpecimenCollection(Base):
    __tablename__ = "specimen_collections"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    specimen_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("specimens.id"), nullable=False
    )
    collector_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    collection_site: Mapped[str | None] = mapped_column(String(128))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)


class SpecimenCustodyEvent(Base):
    __tablename__ = "specimen_custody_events"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    specimen_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("specimens.id"), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class LaboratoryResult(Base):
    __tablename__ = "laboratory_results"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    ordered_test_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ordered_tests.id"), nullable=False
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    reference_range: Mapped[str | None] = mapped_column(String(128))
    interpretation: Mapped[str | None] = mapped_column(String(64))
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PRELIMINARY"
    )
    entered_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("laboratory_orders.id"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PRELIMINARY"
    )
    conclusion: Mapped[str | None] = mapped_column(Text)
    pdf_storage_key: Mapped[str | None] = mapped_column(String(512))
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id")
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_to_patient_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class QualityControlReview(Base):
    __tablename__ = "quality_control_reviews"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    report_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("diagnostic_reports.id"), nullable=False
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ResultCorrection(Base):
    __tablename__ = "result_corrections"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    result_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("laboratory_results.id"), nullable=False
    )
    previous_value: Mapped[str] = mapped_column(String(255), nullable=False)
    corrected_value: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    corrected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class CriticalResultAcknowledgement(Base):
    __tablename__ = "critical_result_acknowledgements"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    result_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("laboratory_results.id"),
        nullable=False,
        unique=True,
    )
    clinician_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    action_taken: Mapped[str | None] = mapped_column(Text)
