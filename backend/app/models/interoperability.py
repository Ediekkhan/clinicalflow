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


class CountryPack(Base):
    __tablename__ = "country_packs"
    __table_args__ = (
        UniqueConstraint("country_code", "version", name="uq_country_pack_version"),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    requires_legal_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class InteroperabilityMapping(Base):
    __tablename__ = "interoperability_mappings"
    __table_args__ = (
        UniqueConstraint(
            "country_pack_id",
            "resource_type",
            "version",
            name="uq_interop_mapping_version",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    country_pack_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("country_packs.id"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    standard: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class OfflineClinicalMutation(Base):
    __tablename__ = "offline_clinical_mutations"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "client_mutation_id", name="uq_offline_account_mutation"
        ),
    )
    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("auth_accounts.id"), nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    client_mutation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    mutation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
