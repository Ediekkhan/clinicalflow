from __future__ import annotations

from fastapi import APIRouter

from app.routes.terminology.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/public/terminology/releases")
async def public_releases(
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list(
        (
            await session.execute(
                select(TerminologyRelease)
                .where(TerminologyRelease.status == "PUBLISHED")
                .order_by(
                    TerminologyRelease.code_system,
                    TerminologyRelease.release_date.desc(),
                )
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(row.id),
            "code_system": row.code_system,
            "version": row.version,
            "language": row.language,
            "release_date": row.release_date,
            "status": row.status,
        }
        for row in rows
    ]


@router.get("/public/terminology/concepts")
async def search_concepts(
    q: str = "",
    concept_type: str | None = None,
    language: str | None = None,
    country: str | None = None,
    code_system: str | None = None,
    limit: int = 30,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    term = normalize_term(q)
    query = (
        select(ClinicalConcept, ConceptDesignation.term)
        .join(TerminologyRelease, TerminologyRelease.id == ClinicalConcept.release_id)
        .outerjoin(
            ConceptDesignation, ConceptDesignation.concept_id == ClinicalConcept.id
        )
        .where(
            TerminologyRelease.status == "PUBLISHED", ClinicalConcept.active.is_(True)
        )
    )
    if concept_type:
        query = query.where(ClinicalConcept.concept_type == concept_type.upper())
    if code_system:
        query = query.where(ClinicalConcept.code_system == code_system)
    if language:
        query = query.where(
            or_(
                ConceptDesignation.language_code == language,
                and_(
                    ConceptDesignation.id.is_(None),
                    TerminologyRelease.language == language,
                ),
            )
        )
    if country:
        query = query.where(
            or_(
                ConceptDesignation.country_code == country.upper(),
                ConceptDesignation.country_code.is_(None),
            )
        )
    if term:
        query = query.where(
            or_(
                ClinicalConcept.external_code == q,
                ClinicalConcept.preferred_name.ilike(f"%{q}%"),
                ConceptDesignation.normalized_term.like(f"%{term}%"),
            )
        )
    rows = list(
        (
            await session.execute(
                query.distinct()
                .order_by(ClinicalConcept.preferred_name)
                .limit(max(1, min(limit, 100)))
            )
        ).all()
    )
    seen: set[uuid.UUID] = set()
    result = []
    for concept, matched in rows:
        if concept.id not in seen:
            result.append(public_concept(concept, matched))
            seen.add(concept.id)
    return result


@router.get("/public/terminology/symptoms")
async def search_symptoms(
    q: str = "",
    language: str | None = None,
    country: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await search_concepts(
        q=q, concept_type="SYMPTOM", language=language, country=country, session=session
    )


@router.get("/public/terminology/concepts/{concept_id}")
async def concept_detail(
    concept_id: str, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    designations = list(
        (
            await session.execute(
                select(ConceptDesignation)
                .where(
                    ConceptDesignation.concept_id == row.id,
                    ConceptDesignation.review_status.in_(["APPROVED", "PUBLISHED"]),
                )
                .order_by(
                    ConceptDesignation.is_preferred.desc(), ConceptDesignation.term
                )
            )
        )
        .scalars()
        .all()
    )
    result = public_concept(row)
    result["designations"] = [
        {
            "term": value.term,
            "language_code": value.language_code,
            "country_code": value.country_code,
            "term_type": value.term_type,
            "is_preferred": value.is_preferred,
        }
        for value in designations
    ]
    return result


@router.get("/public/terminology/concepts/{concept_id}/synonyms")
async def concept_synonyms(
    concept_id: str,
    language: str | None = None,
    country: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    query = select(ConceptDesignation).where(
        ConceptDesignation.concept_id == row.id,
        ConceptDesignation.term_type != "PREFERRED_NAME",
        ConceptDesignation.review_status.in_(["APPROVED", "PUBLISHED"]),
    )
    if language:
        query = query.where(ConceptDesignation.language_code == language)
    if country:
        query = query.where(
            or_(
                ConceptDesignation.country_code == country.upper(),
                ConceptDesignation.country_code.is_(None),
            )
        )
    rows = list(
        (await session.execute(query.order_by(ConceptDesignation.term))).scalars().all()
    )
    return [
        {
            "term": value.term,
            "language_code": value.language_code,
            "country_code": value.country_code,
            "term_type": value.term_type,
        }
        for value in rows
    ]


@router.get("/public/terminology/concepts/{concept_id}/children")
async def concept_children(
    concept_id: str, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    children = list(
        (
            await session.execute(
                select(ClinicalConcept)
                .join(
                    TerminologyRelease,
                    TerminologyRelease.id == ClinicalConcept.release_id,
                )
                .where(
                    ClinicalConcept.parent_concept_id == row.id,
                    TerminologyRelease.status == "PUBLISHED",
                )
                .order_by(ClinicalConcept.preferred_name)
            )
        )
        .scalars()
        .all()
    )
    return [public_concept(value) for value in children]


@router.get("/public/terminology/concepts/{concept_id}/relationships")
async def concept_relationships(
    concept_id: str,
    relationship_type: str | None = None,
    country: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    row = await published_concept(session, parse_uuid(concept_id, "concept_id"))
    query = (
        select(ClinicalRelationship, ClinicalConcept)
        .join(
            ClinicalConcept,
            ClinicalConcept.id == ClinicalRelationship.target_concept_id,
        )
        .join(
            TerminologyRelease, TerminologyRelease.id == ClinicalRelationship.release_id
        )
        .where(
            ClinicalRelationship.source_concept_id == row.id,
            ClinicalRelationship.review_status.in_(["APPROVED", "PUBLISHED"]),
            TerminologyRelease.status == "PUBLISHED",
        )
    )
    if relationship_type:
        query = query.where(
            ClinicalRelationship.relationship_type == relationship_type.upper()
        )
    if country:
        query = query.where(
            or_(
                ClinicalRelationship.country_code == country.upper(),
                ClinicalRelationship.country_code.is_(None),
            )
        )
    rows = list((await session.execute(query)).all())
    return [
        {
            "id": str(value.id),
            "relationship_type": value.relationship_type,
            "target": public_concept(target),
            "evidence_strength": value.evidence_strength,
            "frequency": value.frequency,
            "country_code": value.country_code,
        }
        for value, target in rows
    ]
