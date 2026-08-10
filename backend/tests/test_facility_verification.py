from datetime import UTC, datetime

import pytest

from app.services.facility_verification import review_due_at, transition_case, transition_allowed
from app.services.facility_verification_providers import FacilityRecord, compare_facility


class Case:
    def __init__(self, status: str):
        self.status = status
        self.last_transition_at = None
        self.resolved_at = None


def test_review_sla_skips_weekends():
    due = review_due_at(datetime(2026, 8, 7, 12, tzinfo=UTC))
    assert due.weekday() == 1
    assert due.date().isoformat() == "2026-08-11"


def test_case_transition_updates_audit_timestamps():
    case = Case("UNDER_REVIEW")
    now = datetime(2026, 8, 3, tzinfo=UTC)
    transition_case(case, "APPROVED", now=now)
    assert case.status == "APPROVED"
    assert case.last_transition_at == now
    assert case.resolved_at is None


def test_invalid_case_transition_is_rejected():
    assert transition_allowed("ACTIVE", "REVOKED")
    with pytest.raises(ValueError, match="Invalid facility verification transition"):
        transition_case(Case("SUBMITTED"), "ACTIVE")


def test_registry_matching_blocks_expired_licence():
    result = compare_facility(
        {"legal_name": "Example Hospital", "licence_number": "LIC-1", "registration_number": "REG-1"},
        FacilityRecord("facility-1", legal_name="Example Hospital", licence_number="LIC-1", registration_number="REG-1", licence_status="ACTIVE", expiry_date=datetime(2020, 1, 1, tzinfo=UTC).date()),
    )
    assert result["match_result"] == "EXPIRED"
    assert "licence_expired" in result["blocking_findings"]


def test_registry_matching_returns_exact_match():
    result = compare_facility(
        {"legal_name": "Example Hospital", "licence_number": "LIC-1"},
        FacilityRecord("facility-1", legal_name="Example Hospital", licence_number="LIC-1", licence_status="ACTIVE"),
    )
    assert result["match_result"] == "EXACT_MATCH"
