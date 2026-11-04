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


class SignupApplication(Base):
    __tablename__ = "signup_applications"
    __table_args__ = (
        Index("ix_signup_applications_type_status", "application_type", "status"),
        Index("ix_signup_applications_email", "email"),
        Index("ix_signup_applications_phone", "phone"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    reference: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    application_type: Mapped[str] = mapped_column(String(32), nullable=False)
    onboarding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="DRAFT")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invitation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("staff_invitations.id"), nullable=True
    )
    account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    consent_version: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class OrganizationOnboardingDraft(Base):
    __tablename__ = "organization_onboarding_drafts"
    __table_args__ = (
        UniqueConstraint("account_id", name="uq_organization_onboarding_draft_account"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    organization_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    draft_data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class OrganizationApplication(Base):
    __tablename__ = "organization_applications"
    __table_args__ = (
        Index("ix_organization_applications_status", "verification_status"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    signup_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("signup_applications.id"),
        nullable=False,
        unique=True,
    )
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    licence_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    regulatory_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="PENDING_VERIFICATION"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ProfessionalCredential(Base):
    __tablename__ = "professional_credentials"
    __table_args__ = (
        UniqueConstraint(
            "licence_number",
            "jurisdiction",
            name="uq_professional_credential_jurisdiction",
        ),
        Index("ix_professional_credentials_application", "signup_application_id"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    signup_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False
    )
    licence_number: Mapped[str] = mapped_column(String(128), nullable=False)
    licensing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(128), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="PENDING_VERIFICATION"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class VerificationDocument(Base):
    __tablename__ = "verification_documents"
    __table_args__ = (
        Index("ix_verification_documents_application", "signup_application_id"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    signup_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    private_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("verification_documents.id"), nullable=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="PENDING_VERIFICATION"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ApplicationReviewHistory(Base):
    __tablename__ = "application_review_history"
    __table_args__ = (
        Index(
            "ix_application_review_history_application",
            "signup_application_id",
            "created_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    signup_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False
    )
    reviewer_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class FacilityVerificationCase(Base):
    __tablename__ = "facility_verification_cases"
    __table_args__ = (
        UniqueConstraint(
            "signup_application_id", name="uq_facility_verification_case_application"
        ),
        Index(
            "ix_facility_verification_cases_queue",
            "status",
            "review_due_at",
            "priority",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    signup_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False
    )
    organization_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organization_applications.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="SUBMITTED")
    priority: Mapped[str] = mapped_column(
        String(32), nullable=False, default="STANDARD"
    )
    assigned_reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True, index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    review_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_transition_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    government_check_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    risk_flags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ExternalRegistryCheck(Base):
    __tablename__ = "external_registry_checks"
    __table_args__ = (
        Index("ix_external_registry_checks_case", "verification_case_id", "checked_at"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    verification_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("facility_verification_cases.id"), nullable=False
    )
    registry_code: Mapped[str] = mapped_column(String(64), nullable=False)
    query_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checked_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )


class VerificationFinding(Base):
    __tablename__ = "verification_findings"
    __table_args__ = (
        Index("ix_verification_findings_case_status", "verification_case_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    verification_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("facility_verification_cases.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="INFO")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class FacilityAdminActivation(Base):
    __tablename__ = "facility_admin_activations"
    __table_args__ = (
        Index("ix_facility_admin_activations_token", "token_hash", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    verification_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("facility_verification_cases.id"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class VerificationEvent(Base):
    __tablename__ = "verification_events"
    __table_args__ = (
        Index(
            "ix_verification_events_application_type",
            "signup_application_id",
            "event_type",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    signup_application_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("signup_applications.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
