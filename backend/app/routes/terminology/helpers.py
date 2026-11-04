from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuthAccount,
    ClinicalConcept,
    ClinicalContentReview,
    ClinicalRelationship,
    ConceptDesignation,
    TerminologyRelease,
)
from app.routes.dependencies import get_db, require_account, require_roles
from app.services.auth_service import utc_now


CONCEPT_TYPES = {
    "DISEASE",
    "DISORDER",
    "SYMPTOM",
    "SIGN",
    "SYNDROME",
    "INJURY",
    "CLINICAL_FINDING",
    "BODY_LOCATION",
    "SPECIALTY",
    "PROCEDURE",
}
TERM_TYPES = {
    "PREFERRED_NAME",
    "SYNONYM",
    "ABBREVIATION",
    "COMMON_NAME",
    "LOCAL_EXPRESSION",
    "PATIENT_FRIENDLY",
}
RELATIONSHIP_TYPES = {
    "HAS_FINDING",
    "MAY_HAVE",
    "ASSOCIATED_WITH",
    "IS_RED_FLAG_FOR",
    "ROUTES_TO",
    "PARENT_OF",
    "MAPS_TO",
}
CONTENT_ROLES = {
    "admin",
    "platform-admin",
    "terminology_admin",
    "clinical_reviewer",
    "clinical_publisher",
}


def normalize_term(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", ascii_value)).strip()


def parse_uuid(value: Any, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422, detail=f"A valid {label} is required"
        ) from error


def parse_datetime(value: Any, label: str) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422, detail=f"A valid {label} is required"
        ) from error


def public_concept(
    row: ClinicalConcept, matched_term: str | None = None
) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "code_system": row.code_system,
        "code": row.external_code,
        "concept_type": row.concept_type,
        "preferred_name": row.preferred_name,
        "definition": row.definition,
        "active": row.active,
        "matched_term": matched_term,
    }


async def published_concept(
    session: AsyncSession, concept_id: uuid.UUID
) -> ClinicalConcept:
    row = await session.scalar(
        select(ClinicalConcept)
        .join(TerminologyRelease, TerminologyRelease.id == ClinicalConcept.release_id)
        .where(
            ClinicalConcept.id == concept_id, TerminologyRelease.status == "PUBLISHED"
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Published concept not found")
    return row


async def editable_release(
    session: AsyncSession, release_id: uuid.UUID
) -> TerminologyRelease:
    row = await session.get(TerminologyRelease, release_id)
    if not row:
        raise HTTPException(status_code=404, detail="Terminology release not found")
    if row.status == "PUBLISHED":
        raise HTTPException(
            status_code=409,
            detail="Published releases are immutable; create a new version",
        )
    if row.status == "RETIRED":
        raise HTTPException(
            status_code=409,
            detail="Retired releases remain historical and cannot be edited",
        )
    return row


__all__ = [name for name in globals() if not name.startswith("__")]
