"""Country-configurable facility registry verification primitives.

The provider is deliberately transport-agnostic: a deployment may connect an
authorized government API or import an authorized data file without changing
the reviewer workflow. Manual lookup remains the safe default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


MATCH_RESULTS = {"EXACT_MATCH", "PARTIAL_MATCH", "NOT_FOUND", "EXPIRED", "SUSPENDED", "REVOKED", "MANUAL_REVIEW_REQUIRED", "PROVIDER_UNAVAILABLE"}


@dataclass(slots=True)
class FacilityRecord:
    external_facility_id: str
    legal_name: str | None = None
    registration_number: str | None = None
    licence_number: str | None = None
    facility_type: str | None = None
    address: str | None = None
    jurisdiction: str | None = None
    licence_status: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    registered_operator: str | None = None
    services: list[str] = field(default_factory=list)


class FacilityRegistryProvider(Protocol):
    async def find_by_licence(self, country: str, licence_number: str) -> FacilityRecord | None: ...
    async def find_by_registration(self, country: str, registration_number: str) -> FacilityRecord | None: ...
    async def get_facility(self, country: str, external_facility_id: str) -> FacilityRecord | None: ...


class ManualRegistryProvider:
    async def find_by_licence(self, country: str, licence_number: str) -> FacilityRecord | None:
        return None

    async def find_by_registration(self, country: str, registration_number: str) -> FacilityRecord | None:
        return None

    async def get_facility(self, country: str, external_facility_id: str) -> FacilityRecord | None:
        return None


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def compare_facility(submitted: dict[str, Any], record: FacilityRecord | None) -> dict[str, Any]:
    if record is None:
        return {"match_result": "NOT_FOUND", "match_score": 0, "matched_fields": [], "mismatched_fields": [], "blocking_findings": ["registry_record_not_found"]}
    fields = {"legal_name": record.legal_name, "registration_number": record.registration_number, "licence_number": record.licence_number, "facility_type": record.facility_type, "jurisdiction": record.jurisdiction, "address": record.address}
    matched, mismatched = [], []
    for key, actual in fields.items():
        expected = submitted.get(key)
        if expected in (None, "") or actual in (None, ""):
            continue
        (matched if _norm(expected) == _norm(actual) else mismatched).append(key)
    score = round((len(matched) / max(len(matched) + len(mismatched), 1)) * 100)
    status = _norm(record.licence_status).upper()
    if status in {"REVOKED", "REVOKED_LICENSE"}:
        result = "REVOKED"
    elif status in {"SUSPENDED", "SUSPENDED_LICENSE"}:
        result = "SUSPENDED"
    elif record.expiry_date and record.expiry_date < date.today():
        result = "EXPIRED"
    elif score == 100 and matched:
        result = "EXACT_MATCH"
    else:
        result = "PARTIAL_MATCH" if matched else "MANUAL_REVIEW_REQUIRED"
    blocking = [f"mismatch:{field}" for field in mismatched]
    if result in {"EXPIRED", "SUSPENDED", "REVOKED"}:
        blocking.append(f"licence_{result.casefold()}")
    return {"match_result": result, "match_score": score, "matched_fields": matched, "mismatched_fields": mismatched, "blocking_findings": blocking, "licence_status": record.licence_status}
