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


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (
        UniqueConstraint("country_code", "code", name="uq_medication_country_code"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
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
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    encounter_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("encounters.id")
    )
    prescriber_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    prescriber_membership_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("staff_memberships.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    pharmacy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="NG")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SIGNED")
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    prescription_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False
    )
    medication_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("medications.id"), nullable=False
    )
    dosage: Mapped[str] = mapped_column(String(255), nullable=False)
    route: Mapped[str | None] = mapped_column(String(64))
    frequency: Mapped[str] = mapped_column(String(128), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_dispensed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    substitution_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class PharmacyOrder(Base):
    __tablename__ = "pharmacy_orders"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    prescription_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False, unique=True
    )
    pharmacy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RECEIVED")
    validated_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id")
    )
    validation_notes: Mapped[str | None] = mapped_column(Text)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint(
            "pharmacy_id",
            "medication_id",
            "batch_number",
            name="uq_inventory_medication_batch",
        ),
        Index("ix_inventory_expiry", "pharmacy_id", "expires_at"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    pharmacy_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    medication_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("medications.id"), nullable=False
    )
    batch_number: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    inventory_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False
    )
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64))
    reference_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    actor_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DispenseEvent(Base):
    __tablename__ = "dispense_events"
    __table_args__ = (
        UniqueConstraint(
            "prescription_item_id",
            "idempotency_key",
            name="uq_dispense_item_idempotency",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    pharmacy_order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacy_orders.id"), nullable=False
    )
    prescription_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prescription_items.id"), nullable=False
    )
    inventory_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    dispenser_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    dispensed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SubstitutionRequest(Base):
    __tablename__ = "substitution_requests"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    prescription_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prescription_items.id"), nullable=False
    )
    proposed_medication_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("medications.id"), nullable=False
    )
    requested_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    decided_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id")
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InteractionAlert(Base):
    __tablename__ = "interaction_alerts"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    prescription_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("prescriptions.id"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ControlledMedicationLog(Base):
    __tablename__ = "controlled_medication_logs"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    dispense_event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("dispense_events.id"),
        nullable=False,
        unique=True,
    )
    schedule: Mapped[str] = mapped_column(String(32), nullable=False)
    witness_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    register_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PharmacyDelivery(Base):
    __tablename__ = "pharmacy_deliveries"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    pharmacy_order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacy_orders.id"), nullable=False
    )
    delivery_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PICKUP"
    )
    masked_destination: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PatientCounselling(Base):
    __tablename__ = "patient_counselling"
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    pharmacy_order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacy_orders.id"), nullable=False
    )
    pharmacist_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    topics_json: Mapped[str] = mapped_column(Text, nullable=False)
    patient_understood: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    counselled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
