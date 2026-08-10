from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ClinicalConcept,
    ClinicalContentReview,
    ClinicalRelationship,
    ConceptDesignation,
    TerminologyRelease,
)
from app.services.knowledge_graph import SYMPTOM_ALIASES
from app.terminology_routes import normalize_term


class TerminologyImportError(ValueError):
    pass


@dataclass(frozen=True)
class ImportResult:
    release_id: UUID
    created: bool
    concepts: int
    designations: int
    relationships: int


LOCAL_NAMES = {
    "chest_pain": "Chest pain",
    "difficulty_breathing": "Difficulty breathing",
    "severe_bleeding": "Severe bleeding",
    "fever": "Fever",
    "cough": "Cough",
    "headache": "Headache",
    "vomiting": "Vomiting",
    "dizziness": "Dizziness",
    "rash": "Rash",
    "weakness": "Weakness",
}


def checksum_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def local_payload() -> dict[str, Any]:
    concepts = []
    for code, aliases in SYMPTOM_ALIASES.items():
        preferred = LOCAL_NAMES[code]
        concepts.append(
            {
                "code": code,
                "type": "SYMPTOM",
                "name": preferred,
                "definition": None,
                "designations": [
                    {
                        "term": alias,
                        "language": "pcm" if alias in {"pain for chest", "body hot", "head dey pain", "body weak"} else "en",
                        "country": "NG",
                        "type": "LOCAL_EXPRESSION" if alias != preferred.casefold() else "PREFERRED_NAME",
                        "review_status": "DRAFT",
                    }
                    for alias in aliases
                ],
            }
        )
    return {
        "metadata": {
            "code_system": "CLINICALFLOW_LOCAL",
            "language": "en",
            "licence": "ClinicalFlow clinician-reviewed local terminology",
        },
        "concepts": concepts,
        "relationships": [],
        "scope_note": "Initial engineering seed only; not a comprehensive medical catalogue.",
    }


def read_source(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise TerminologyImportError(f"Source file does not exist: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TerminologyImportError("Terminology source must be valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise TerminologyImportError("Terminology source root must be an object")
    return payload, checksum_bytes(raw)


def validate_payload(payload: dict[str, Any], *, expected_system: str | None = None) -> list[str]:
    errors: list[str] = []
    metadata = payload.get("metadata")
    concepts = payload.get("concepts")
    relationships = payload.get("relationships", [])
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
        metadata = {}
    if expected_system and str(metadata.get("code_system", "")).upper() != expected_system.upper():
        errors.append(f"metadata.code_system must be {expected_system}")
    if not str(metadata.get("licence") or "").strip():
        errors.append("metadata.licence is required")
    if not isinstance(concepts, list) or not concepts:
        errors.append("concepts must be a non-empty array")
        concepts = []
    if not isinstance(relationships, list):
        errors.append("relationships must be an array")
    codes: set[str] = set()
    for index, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            errors.append(f"concepts[{index}] must be an object")
            continue
        code = str(concept.get("code") or "").strip()
        if not code or not str(concept.get("name") or "").strip() or not str(concept.get("type") or "").strip():
            errors.append(f"concepts[{index}] requires code, name and type")
        if code in codes:
            errors.append(f"duplicate concept code: {code}")
        codes.add(code)
    return errors


async def import_payload(
    session: AsyncSession,
    *,
    payload: dict[str, Any],
    version: str,
    checksum: str,
    source_url: str | None = None,
    expected_system: str | None = None,
) -> ImportResult:
    errors = validate_payload(payload, expected_system=expected_system)
    if errors:
        raise TerminologyImportError("; ".join(errors))
    metadata = payload["metadata"]
    code_system = str(metadata["code_system"]).upper()
    language = str(metadata.get("language") or "en").lower()
    existing = await session.scalar(
        select(TerminologyRelease).where(
            TerminologyRelease.code_system == code_system,
            TerminologyRelease.version == version,
            TerminologyRelease.language == language,
        )
    )
    if existing:
        if existing.checksum != checksum:
            raise TerminologyImportError("Release version already exists with a different checksum")
        counts = await release_counts(session, existing.id)
        return ImportResult(existing.id, False, *counts)

    release = TerminologyRelease(
        code_system=code_system,
        version=version,
        source_url=source_url,
        license_reference=str(metadata["licence"]).strip(),
        language=language,
        checksum=checksum,
        status="DRAFT",
    )
    session.add(release)
    await session.flush()
    by_code: dict[str, ClinicalConcept] = {}
    designation_count = 0
    for value in payload["concepts"]:
        concept = ClinicalConcept(
            release_id=release.id,
            code_system=code_system,
            external_code=str(value["code"]).strip(),
            concept_type=str(value["type"]).upper(),
            preferred_name=str(value["name"]).strip(),
            definition=str(value.get("definition") or "").strip() or None,
            active=bool(value.get("active", True)),
        )
        session.add(concept)
        await session.flush()
        by_code[concept.external_code] = concept
        terms = value.get("designations", [])
        if not isinstance(terms, list):
            raise TerminologyImportError(f"Designations for {concept.external_code} must be an array")
        for term in terms:
            text = str(term.get("term") or "").strip()
            if not text:
                continue
            session.add(
                ConceptDesignation(
                    concept_id=concept.id,
                    language_code=str(term.get("language") or language).lower(),
                    country_code=str(term["country"]).upper() if term.get("country") else None,
                    term=text,
                    normalized_term=normalize_term(text),
                    term_type=str(term.get("type") or "SYNONYM").upper(),
                    is_preferred=bool(term.get("preferred", False)),
                    review_status=str(term.get("review_status") or "DRAFT").upper(),
                )
            )
            designation_count += 1
    relationship_count = 0
    for value in payload.get("relationships", []):
        source = by_code.get(str(value.get("source_code") or ""))
        target = by_code.get(str(value.get("target_code") or ""))
        if not source or not target or source.id == target.id:
            raise TerminologyImportError("Every relationship must reference two different imported concept codes")
        session.add(
            ClinicalRelationship(
                source_concept_id=source.id,
                target_concept_id=target.id,
                relationship_type=str(value.get("type") or "").upper(),
                release_id=release.id,
                country_code=str(value["country"]).upper() if value.get("country") else None,
                source_reference=str(value.get("source_reference") or "").strip() or None,
                review_status="DRAFT",
            )
        )
        relationship_count += 1
    await session.commit()
    return ImportResult(release.id, True, len(by_code), designation_count, relationship_count)


async def release_counts(session: AsyncSession, release_id: UUID) -> tuple[int, int, int]:
    concepts = list((await session.execute(select(ClinicalConcept).where(ClinicalConcept.release_id == release_id))).scalars())
    concept_ids = [row.id for row in concepts]
    designations = list((await session.execute(select(ConceptDesignation).where(ConceptDesignation.concept_id.in_(concept_ids)))).scalars()) if concept_ids else []
    relationships = list((await session.execute(select(ClinicalRelationship).where(ClinicalRelationship.release_id == release_id))).scalars())
    return len(concepts), len(designations), len(relationships)


async def validate_release(session: AsyncSession, release_id: UUID) -> dict[str, Any]:
    release = await session.get(TerminologyRelease, release_id)
    if not release:
        raise TerminologyImportError("Terminology release not found")
    concepts, designations, relationships = await release_counts(session, release.id)
    errors = []
    if not release.license_reference.strip():
        errors.append("Licence reference is missing")
    if not release.checksum.strip():
        errors.append("Checksum is missing")
    if concepts == 0:
        errors.append("Release has no concepts")
    return {
        "release_id": str(release.id),
        "status": release.status,
        "valid": not errors,
        "errors": errors,
        "concepts": concepts,
        "designations": designations,
        "relationships": relationships,
    }


async def publish_release(session: AsyncSession, release_id: UUID, publisher_id: UUID) -> TerminologyRelease:
    release = await session.get(TerminologyRelease, release_id)
    if not release or release.status == "RETIRED":
        raise TerminologyImportError("Publishable release not found")
    if release.status == "PUBLISHED":
        return release
    report = await validate_release(session, release.id)
    review = await session.scalar(
        select(ClinicalContentReview).where(
            ClinicalContentReview.resource_type == "TerminologyRelease",
            ClinicalContentReview.resource_id == release.id,
            ClinicalContentReview.decision == "APPROVED",
            ClinicalContentReview.reviewer_account_id != publisher_id,
        )
    )
    if not report["valid"] or not review or release.status != "APPROVED":
        raise TerminologyImportError("A valid release and separate approved clinical review are required")
    release.status = "PUBLISHED"
    await session.commit()
    return release


async def rollback_release(session: AsyncSession, release_id: UUID, restore_release_id: UUID) -> None:
    current = await session.get(TerminologyRelease, release_id)
    restore = await session.get(TerminologyRelease, restore_release_id)
    if not current or current.status != "PUBLISHED":
        raise TerminologyImportError("Current release must be published")
    if not restore or restore.code_system != current.code_system or restore.id == current.id:
        raise TerminologyImportError("Rollback target must be a different release in the same code system")
    if restore.status not in {"PUBLISHED", "RETIRED"}:
        raise TerminologyImportError("Rollback target must have been previously published")
    current.status = "RETIRED"
    restore.status = "PUBLISHED"
    await session.commit()
