from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CountryPack, InteroperabilityMapping

NIGERIA_POLICY: dict[str, Any] = {
    "country": {"code": "NG", "name": "Nigeria", "jurisdictions": ["FEDERAL", "STATE", "LGA"]},
    "languages": ["en", "ha", "ig", "yo"],
    "currency": "NGN",
    "timezone": "Africa/Lagos",
    "formats": {"date": "dd/MM/yyyy", "number_locale": "en-NG", "phone_prefix": "+234"},
    "emergency_numbers": ["112"],
    "patient_identity_types": ["HEALTH_CARD", "NIN", "PASSPORT", "BIRTH_REGISTRATION"],
    "facility_types": ["HOSPITAL", "CLINIC", "PHARMACY", "LABORATORY", "PRIMARY_HEALTH_CENTRE"],
    "professional_roles": ["DOCTOR", "NURSE", "PHARMACIST", "LAB_SCIENTIST", "MIDWIFE"],
    "licence_authorities": ["MDCN", "NMCN", "PCN", "MLSCN"],
    "consent": {"age_of_consent": 18, "care_delivery_basis": "CONSENT_OR_OTHER_LAWFUL_BASIS"},
    "retention": {"clinical_years": 10, "audit_years": 7},
    "data_residency": {"region": "NG", "cross_border_requires_review": True},
    "prescription": {"default_valid_days": 30, "allowed_prescriber_roles": ["doctor", "specialist"], "generic_substitution_default": False},
    "controlled_medicines": {"witness_required": True, "register_required": True},
    "payer_terminology": {"organization": "HMO or payer", "member": "enrollee"},
    "mandatory_reporting": {"identifiable_requires_authority": True, "small_cell_suppression": 5},
    "clinical_codes": {"diagnosis": ["ICD-10"], "laboratory": ["LOINC"]},
    "interoperability_profile": "NG-FHIR-FOUNDATION-0.1",
    "result_release": {"critical_requires_clinician_acknowledgement": True, "default": "AFTER_FINAL"},
    "emergency_authorization": {"routine_authorization_must_not_block": True},
    "contact_validation": {"country_calling_code": "+234"},
    "legal_review": {"required": True, "disclaimer": "Configuration requires review by qualified Nigerian legal and healthcare authorities."},
}

FHIR_MAPPINGS = {
    "Patient": "Patient", "Facility": "Organization|Location|HealthcareService",
    "Staff": "Practitioner|PractitionerRole", "Appointment": "Appointment|Schedule|Slot",
    "Visit": "Encounter", "Diagnosis": "Condition", "LaboratoryOrder": "ServiceRequest",
    "LaboratoryResult": "Observation|DiagnosticReport", "Prescription": "MedicationRequest",
    "Dispensing": "MedicationDispense", "Coverage": "Coverage", "Claim": "Claim|ClaimResponse",
    "Consent": "Consent", "Audit": "AuditEvent|Provenance",
}


async def ensure_nigeria_country_pack(session: AsyncSession) -> CountryPack:
    row = await session.scalar(select(CountryPack).where(CountryPack.country_code == "NG", CountryPack.version == "2026.1"))
    if row:
        return row
    row = CountryPack(country_code="NG", version="2026.1", status="ACTIVE", policy_json=json.dumps(NIGERIA_POLICY), requires_legal_review=True)
    session.add(row); await session.flush()
    session.add_all([InteroperabilityMapping(country_pack_id=row.id, resource_type=resource, standard="HL7_FHIR", version="R4", mapping_json=json.dumps({"target": target}), status="ACTIVE") for resource, target in FHIR_MAPPINGS.items()])
    return row


async def country_policy(session: AsyncSession, country_code: str = "NG", at: datetime | None = None) -> dict[str, Any]:
    query = select(CountryPack).where(CountryPack.country_code == country_code.upper(), CountryPack.status == "ACTIVE").order_by(CountryPack.effective_from.desc(), CountryPack.created_at.desc())
    row = await session.scalar(query)
    if not row and country_code.upper() == "NG":
        row = await ensure_nigeria_country_pack(session)
    return json.loads(row.policy_json) if row else {}


def nested_policy(policy: dict[str, Any], *path: str, default: Any = None) -> Any:
    value: Any = policy
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value
