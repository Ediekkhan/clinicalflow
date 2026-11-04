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


class TerminologyRelease(Base):
    __tablename__ = "terminology_releases"
    __table_args__ = (
        UniqueConstraint(
            "code_system", "version", "language", name="uq_terminology_release_version"
        ),
        Index("ix_terminology_releases_status_system", "status", "code_system"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    code_system: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(String(1024))
    license_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class ClinicalConcept(Base):
    __tablename__ = "clinical_concepts"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "code_system",
            "external_code",
            name="uq_clinical_concept_release_code",
        ),
        Index(
            "ix_clinical_concepts_search", "concept_type", "active", "preferred_name"
        ),
        Index("ix_clinical_concepts_external_code", "code_system", "external_code"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    release_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("terminology_releases.id"), nullable=False
    )
    code_system: Mapped[str] = mapped_column(String(128), nullable=False)
    external_code: Mapped[str] = mapped_column(String(128), nullable=False)
    concept_type: Mapped[str] = mapped_column(String(32), nullable=False)
    preferred_name: Mapped[str] = mapped_column(String(512), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text)
    parent_concept_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clinical_concepts.id")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ConceptDesignation(Base):
    __tablename__ = "concept_designations"
    __table_args__ = (
        UniqueConstraint(
            "concept_id",
            "language_code",
            "country_code",
            "normalized_term",
            "term_type",
            name="uq_concept_designation_term",
        ),
        Index(
            "ix_concept_designations_search",
            "normalized_term",
            "language_code",
            "country_code",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(16), nullable=False)
    country_code: Mapped[str | None] = mapped_column(String(2))
    term: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_term: Mapped[str] = mapped_column(String(512), nullable=False)
    term_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT"
    )


class ClinicalRelationship(Base):
    __tablename__ = "clinical_relationships"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "source_concept_id",
            "relationship_type",
            "target_concept_id",
            "country_code",
            name="uq_clinical_relationship_release",
        ),
        Index(
            "ix_clinical_relationships_source_type",
            "source_concept_id",
            "relationship_type",
        ),
        Index(
            "ix_clinical_relationships_target_type",
            "target_concept_id",
            "relationship_type",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    source_concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_concept_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clinical_concepts.id"), nullable=False
    )
    evidence_strength: Mapped[str | None] = mapped_column(String(32))
    frequency: Mapped[str | None] = mapped_column(String(32))
    age_group: Mapped[str | None] = mapped_column(String(32))
    sex_applicability: Mapped[str | None] = mapped_column(String(32))
    pregnancy_applicability: Mapped[str | None] = mapped_column(String(32))
    country_code: Mapped[str | None] = mapped_column(String(2))
    source_reference: Mapped[str | None] = mapped_column(String(1024))
    release_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("terminology_releases.id"), nullable=False
    )
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DRAFT"
    )


class ClinicalContentReview(Base):
    __tablename__ = "clinical_content_reviews"
    __table_args__ = (
        Index(
            "ix_clinical_content_reviews_resource",
            "resource_type",
            "resource_id",
            "reviewed_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reviewer_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    reviewer_role: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer_organization_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id")
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(1024))
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
