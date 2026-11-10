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


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_tenant_queue", "tenant_id", "queue_status"),
        Index("ix_tickets_tenant_phone", "tenant_id", "customer_phone"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    ticket_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_intake_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_group_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="WEB")
    urgency_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="ROUTINE"
    )
    matched_condition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    terminology_release_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("terminology_releases.id"),
        nullable=True,
        index=True,
    )
    assigned_specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    queue_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="QUEUED"
    )
    is_manually_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    appointment_slot: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    patient_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    routed_tenant_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    route_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    assigned_specialist_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    tenant: Mapped[Tenant] = relationship(
        back_populates="tickets", foreign_keys=[tenant_id]
    )


class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    __table_args__ = (
        UniqueConstraint("ticket_id", name="uq_routing_decision_ticket"),
        Index(
            "ix_routing_decisions_destination_created",
            "selected_facility_id",
            "created_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    ticket_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False
    )
    patient_owner_tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    selected_facility_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    required_service: Mapped[str | None] = mapped_column(String(128), nullable=True)
    required_specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    urgency: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SELECTED")
    selection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_preference_facility_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    manual_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    overridden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    patient_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    selected_hospital_country_code: Mapped[str | None] = mapped_column(
        String(2), nullable=True
    )
    cross_border: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eligibility_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_candidates: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    routing_policy_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="country-first-v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class RoutingCandidate(Base):
    __tablename__ = "routing_candidates"
    __table_args__ = (
        UniqueConstraint(
            "routing_decision_id", "facility_id", name="uq_routing_candidate_facility"
        ),
        Index("ix_routing_candidates_decision_rank", "routing_decision_id", "rank"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    routing_decision_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("routing_decisions.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    suitability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    has_required_capability: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    has_emergency_capability: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    has_staff_coverage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    has_capacity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class FacilityAcceptance(Base):
    __tablename__ = "facility_acceptances"
    __table_args__ = (
        Index("ix_facility_acceptances_ticket_created", "ticket_id", "created_at"),
        Index("ix_facility_acceptances_facility_status", "facility_id", "decision"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    ticket_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tickets.id"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    actor_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    actor_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("staff_memberships.id")
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    next_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    redirected_facility_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
