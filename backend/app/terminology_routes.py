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
from app.routes import get_db, require_account, require_roles
from app.services.auth_service import utc_now

router = APIRouter(prefix="/api/v1")

CONCEPT_TYPES = {
    "DISEASE", "DISORDER", "SYMPTOM", "SIGN", "SYNDROME", "INJURY",
    "CLINICAL_FINDING", "BODY_LOCATION", "SPECIALTY", "PROCEDURE",
}
TERM_TYPES = {"PREFERRED_NAME", "SYNONYM", "ABBREVIATION", "COMMON_NAME", "LOCAL_EXPRESSION", "PATIENT_FRIENDLY"}
RELATIONSHIP_TYPES = {"HAS_FINDING", "MAY_HAVE", "ASSOCIATED_WITH", "IS_RED_FLAG_FOR", "ROUTES_TO", "PARENT_OF", "MAPS_TO"}
CONTENT_ROLES = {"admin", "platform-admin", "terminology_admin", "clinical_reviewer", "clinical_publisher"}


def normalize_term(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", ascii_value)).strip()


def parse_uuid(value: Any, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"A valid {label} is required") from error


def parse_datetime(value: Any, label: str) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"A valid {label} is required") from error


def public_concept(row: ClinicalConcept, matched_term: str | None = None) -> dict[str, Any]:
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


async def published_concept(session: AsyncSession, concept_id: uuid.UUID) -> ClinicalConcept:
    row = await session.scalar(
        select(ClinicalConcept)
        .join(TerminologyRelease, TerminologyRelease.id == ClinicalConcept.release_id)
        .where(ClinicalConcept.id == concept_id, TerminologyRelease.status == "PUBLISHED")
    )
    if not row:
        raise HTTPException(status_code=404, detail="Published concept not found")
    return row


async def editable_release(session: AsyncSession, release_id: uuid.UUID) -> TerminologyRelease:
    row = await session.get(TerminologyRelease, release_id)
    if not row:
        raise HTTPException(status_code=404, detail="Terminology release not found")
    if row.status == "PUBLISHED":
        raise HTTPException(status_code=409, detail="Published releases are immutable; create a new version")
    if row.status == "RETIRED":
        raise HTTPException(status_code=409, detail="Retired releases remain historical and cannot be edited")
    return row


@router.get("/public/terminology/releases")
async def public_releases(session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = list((await session.execute(select(TerminologyRelease).where(TerminologyRelease.status == "PUBLISHED").order_by(TerminologyRelease.code_system, TerminologyRelease.release_date.desc()))).scalars().all())
    return [{"id": str(row.id), "code_system": row.code_system, "version": row.version, "language": row.language, "release_date": row.release_date, "status": row.status} for row in rows]


@router.get("/public/terminology/concepts")
async def search_concepts(q: str = "", concept_type: str | None = None, language: str | None = None, country: str | None = None, code_system: str | None = None, limit: int = 30, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    term = normalize_term(q)
    query = (
        select(ClinicalConcept, ConceptDesignation.term)
        .join(TerminologyRelease, TerminologyRelease.id == ClinicalConcept.release_id)
        .outerjoin(ConceptDesignation, ConceptDesignation.concept_id == ClinicalConcept.id)
        .where(TerminologyRelease.status == "PUBLISHED", ClinicalConcept.active.is_(True))
    )
    if concept_type:
        query = query.where(ClinicalConcept.concept_type == concept_type.upper())
    if code_system:
        query = query.where(ClinicalConcept.code_system == code_system)
    if language:
        query = query.where(or_(ConceptDesignation.language_code == language, and_(ConceptDesignation.id.is_(None), TerminologyRelease.language == language)))
    if country:
        query = query.where(or_(ConceptDesignation.country_code == country.upper(), ConceptDesignation.country_code.is_(None)))
    if term:
        query = query.where(or_(ClinicalConcept.external_code == q, ClinicalConcept.preferred_name.ilike(f"%{q}%"), ConceptDesignation.normalized_term.like(f"%{term}%")))
    rows = list((await session.execute(query.distinct().order_by(ClinicalConcept.preferred_name).limit(max(1, min(limit, 100))))).all())
    seen: set[uuid.UUID] = set()
    result = []
    for concept, matched in rows:
        if concept.id not in seen:
            result.append(public_concept(concept, matched))
            seen.add(concept.id)
    return result


@router.get("/public/terminology/symptoms")
async def search_symptoms(q: str = "", language: str | None = None, country: str | None = None, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    return await search_concepts(q=q, concept_type="SYMPTOM", language=language, country=country, session=session)


@router.get("/public/terminology/concepts/{concept_id}")
async def concept_detail(concept_id: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    designations = list((await session.execute(select(ConceptDesignation).where(ConceptDesignation.concept_id == row.id, ConceptDesignation.review_status.in_(["APPROVED", "PUBLISHED"])).order_by(ConceptDesignation.is_preferred.desc(), ConceptDesignation.term))).scalars().all())
    result = public_concept(row)
    result["designations"] = [{"term": value.term, "language_code": value.language_code, "country_code": value.country_code, "term_type": value.term_type, "is_preferred": value.is_preferred} for value in designations]
    return result


@router.get("/public/terminology/concepts/{concept_id}/synonyms")
async def concept_synonyms(concept_id: str, language: str | None = None, country: str | None = None, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    query = select(ConceptDesignation).where(ConceptDesignation.concept_id == row.id, ConceptDesignation.term_type != "PREFERRED_NAME", ConceptDesignation.review_status.in_(["APPROVED", "PUBLISHED"]))
    if language:
        query = query.where(ConceptDesignation.language_code == language)
    if country:
        query = query.where(or_(ConceptDesignation.country_code == country.upper(), ConceptDesignation.country_code.is_(None)))
    rows = list((await session.execute(query.order_by(ConceptDesignation.term))).scalars().all())
    return [{"term": value.term, "language_code": value.language_code, "country_code": value.country_code, "term_type": value.term_type} for value in rows]


@router.get("/public/terminology/concepts/{concept_id}/children")
async def concept_children(concept_id: str, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    children = list((await session.execute(select(ClinicalConcept).join(TerminologyRelease, TerminologyRelease.id == ClinicalConcept.release_id).where(ClinicalConcept.parent_concept_id == row.id, TerminologyRelease.status == "PUBLISHED").order_by(ClinicalConcept.preferred_name))).scalars().all())
    return [public_concept(value) for value in children]


@router.get("/public/terminology/concepts/{concept_id}/relationships")
async def concept_relationships(concept_id: str, relationship_type: str | None = None, country: str | None = None, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    query = select(ClinicalRelationship, ClinicalConcept).join(ClinicalConcept, ClinicalConcept.id == ClinicalRelationship.target_concept_id).join(TerminologyRelease, TerminologyRelease.id == ClinicalRelationship.release_id).where(ClinicalRelationship.source_concept_id == row.id, ClinicalRelationship.review_status.in_(["APPROVED", "PUBLISHED"]), TerminologyRelease.status == "PUBLISHED")
    if relationship_type:
        query = query.where(ClinicalRelationship.relationship_type == relationship_type.upper())
    if country:
        query = query.where(or_(ClinicalRelationship.country_code == country.upper(), ClinicalRelationship.country_code.is_(None)))
    rows = list((await session.execute(query)).all())
    return [{"id": str(value.id), "relationship_type": value.relationship_type, "target": public_concept(target), "evidence_strength": value.evidence_strength, "frequency": value.frequency, "country_code": value.country_code} for value, target in rows]


@router.get("/terminology/releases")
async def admin_releases(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    await require_roles(request, session, CONTENT_ROLES)
    rows = list((await session.execute(select(TerminologyRelease).order_by(TerminologyRelease.imported_at.desc()))).scalars().all())
    return [{"id": str(row.id), "code_system": row.code_system, "version": row.version, "language": row.language, "status": row.status, "release_date": row.release_date, "source_url": row.source_url, "license_reference": row.license_reference, "checksum": row.checksum, "imported_at": row.imported_at} for row in rows]


@router.post("/terminology/releases", status_code=201)
async def create_release(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await require_roles(request, session, CONTENT_ROLES)
    payload = await request.json()
    required = {key: str(payload.get(key) or "").strip() for key in ("code_system", "version", "license_reference", "checksum")}
    if not all(required.values()):
        raise HTTPException(status_code=422, detail="Code system, version, licence reference, and checksum are required")
    row = TerminologyRelease(code_system=required["code_system"], version=required["version"], release_date=parse_datetime(payload.get("release_date"), "release_date"), source_url=str(payload.get("source_url") or "").strip() or None, license_reference=required["license_reference"], language=str(payload.get("language") or "en").lower(), checksum=required["checksum"], status="DRAFT")
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Terminology release version already exists") from error
    return {"id": str(row.id), "status": row.status, "code_system": row.code_system, "version": row.version}


@router.post("/terminology/releases/{release_id}/concepts", status_code=201)
async def create_concept(release_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await require_roles(request, session, CONTENT_ROLES)
    release = await editable_release(session, parse_uuid(release_id, "release_id"))
    payload = await request.json()
    concept_type = str(payload.get("concept_type") or "").upper()
    code, name = str(payload.get("external_code") or "").strip(), str(payload.get("preferred_name") or "").strip()
    if concept_type not in CONCEPT_TYPES or not code or not name:
        raise HTTPException(status_code=422, detail="Supported concept type, external code, and preferred name are required")
    row = ClinicalConcept(release_id=release.id, code_system=release.code_system, external_code=code, concept_type=concept_type, preferred_name=name, definition=str(payload.get("definition") or "").strip() or None, parent_concept_id=parse_uuid(payload["parent_concept_id"], "parent_concept_id") if payload.get("parent_concept_id") else None, active=bool(payload.get("active", True)))
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Concept code already exists in this release") from error
    return public_concept(row)


@router.post("/terminology/concepts/{concept_id}/designations", status_code=201)
async def create_designation(concept_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await require_roles(request, session, CONTENT_ROLES)
    concept = await session.get(ClinicalConcept, parse_uuid(concept_id, "concept_id"))
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    await editable_release(session, concept.release_id)
    payload = await request.json()
    term, term_type = str(payload.get("term") or "").strip(), str(payload.get("term_type") or "").upper()
    if not term or term_type not in TERM_TYPES:
        raise HTTPException(status_code=422, detail="Term and supported term type are required")
    row = ConceptDesignation(concept_id=concept.id, language_code=str(payload.get("language_code") or "en").lower(), country_code=str(payload["country_code"]).upper() if payload.get("country_code") else None, term=term, normalized_term=normalize_term(term), term_type=term_type, is_preferred=bool(payload.get("is_preferred")), review_status=str(payload.get("review_status") or "DRAFT").upper())
    session.add(row)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Designation already exists") from error
    return {"id": str(row.id), "term": row.term, "normalized_term": row.normalized_term, "review_status": row.review_status}


@router.post("/terminology/releases/{release_id}/relationships", status_code=201)
async def create_relationship(release_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await require_roles(request, session, CONTENT_ROLES)
    release = await editable_release(session, parse_uuid(release_id, "release_id"))
    payload = await request.json()
    relationship_type = str(payload.get("relationship_type") or "").upper()
    source_id, target_id = parse_uuid(payload.get("source_concept_id"), "source_concept_id"), parse_uuid(payload.get("target_concept_id"), "target_concept_id")
    source, target = await session.get(ClinicalConcept, source_id), await session.get(ClinicalConcept, target_id)
    if relationship_type not in RELATIONSHIP_TYPES or not source or not target or source.release_id != release.id or target.release_id != release.id or source.id == target.id:
        raise HTTPException(status_code=422, detail="A supported relationship between two different concepts in this release is required")
    row = ClinicalRelationship(source_concept_id=source.id, relationship_type=relationship_type, target_concept_id=target.id, evidence_strength=payload.get("evidence_strength"), frequency=payload.get("frequency"), age_group=payload.get("age_group"), sex_applicability=payload.get("sex_applicability"), pregnancy_applicability=payload.get("pregnancy_applicability"), country_code=str(payload["country_code"]).upper() if payload.get("country_code") else None, source_reference=str(payload.get("source_reference") or "").strip() or None, release_id=release.id, review_status=str(payload.get("review_status") or "DRAFT").upper())
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "relationship_type": row.relationship_type, "review_status": row.review_status}


@router.post("/terminology/releases/{release_id}/reviews", status_code=201)
async def review_release(release_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CONTENT_ROLES)
    release = await editable_release(session, parse_uuid(release_id, "release_id"))
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=422, detail="Review decision must be APPROVED or REJECTED")
    row = ClinicalContentReview(resource_type="TerminologyRelease", resource_id=release.id, reviewer_account_id=account.id, reviewer_role=account.role, reviewer_organization_id=account.tenant_id, decision=decision, comments=str(payload.get("comments") or "").strip() or None, evidence_reference=str(payload.get("evidence_reference") or "").strip() or None, next_review_at=parse_datetime(payload.get("next_review_at"), "next_review_at"))
    session.add(row)
    release.status = "APPROVED" if decision == "APPROVED" else "DRAFT"
    await session.commit()
    return {"id": str(row.id), "decision": row.decision, "release_status": release.status}


@router.post("/terminology/releases/{release_id}/publish")
async def publish_release(release_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin", "platform-admin", "clinical_publisher"})
    release = await editable_release(session, parse_uuid(release_id, "release_id"))
    review = await session.scalar(select(ClinicalContentReview).where(ClinicalContentReview.resource_type == "TerminologyRelease", ClinicalContentReview.resource_id == release.id, ClinicalContentReview.decision == "APPROVED", ClinicalContentReview.reviewer_account_id != account.id).order_by(ClinicalContentReview.reviewed_at.desc()))
    if release.status != "APPROVED" or not review:
        raise HTTPException(status_code=409, detail="A separate approved clinical review is required before publication")
    release.status = "PUBLISHED"
    designations = list((await session.execute(select(ConceptDesignation).join(ClinicalConcept, ClinicalConcept.id == ConceptDesignation.concept_id).where(ClinicalConcept.release_id == release.id, ConceptDesignation.review_status == "APPROVED"))).scalars().all())
    relationships = list((await session.execute(select(ClinicalRelationship).where(ClinicalRelationship.release_id == release.id, ClinicalRelationship.review_status == "APPROVED"))).scalars().all())
    for row in designations:
        row.review_status = "PUBLISHED"
    for row in relationships:
        row.review_status = "PUBLISHED"
    await session.commit()
    return {"id": str(release.id), "status": release.status, "published_by": str(account.id), "review_id": str(review.id)}


@router.get("/terminology/resolve")
async def resolve_historical(code_system: str, code: str, version: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await require_account(request, session)
    row = await session.scalar(select(ClinicalConcept).join(TerminologyRelease, TerminologyRelease.id == ClinicalConcept.release_id).where(ClinicalConcept.code_system == code_system, ClinicalConcept.external_code == code, TerminologyRelease.version == version))
    if not row:
        raise HTTPException(status_code=404, detail="Historical concept not found")
    return public_concept(row) | {"release_id": str(row.release_id), "historical": True}


def register_terminology_routes(app) -> None:
    app.include_router(router)
