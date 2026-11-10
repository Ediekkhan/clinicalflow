from __future__ import annotations

from datetime import UTC, datetime, timedelta


FACILITY_VERIFICATION_STATES = {
    "SUBMITTED", "REGISTRY_CHECK_PENDING", "REGISTRY_CHECK_COMPLETED",
    "UNDER_REVIEW", "MORE_INFORMATION_REQUIRED", "RESUBMITTED", "APPROVED",
    "REJECTED", "ADMIN_ACTIVATION_PENDING", "SETUP_REQUIRED", "READINESS_REVIEW",
    "ACTIVE", "SUSPENDED", "REVOKED",
}

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "SUBMITTED": {"REGISTRY_CHECK_PENDING", "UNDER_REVIEW", "REJECTED"},
    "REGISTRY_CHECK_PENDING": {"REGISTRY_CHECK_COMPLETED", "UNDER_REVIEW", "MORE_INFORMATION_REQUIRED"},
    "REGISTRY_CHECK_COMPLETED": {"UNDER_REVIEW", "MORE_INFORMATION_REQUIRED", "REJECTED"},
    "UNDER_REVIEW": {"MORE_INFORMATION_REQUIRED", "APPROVED", "REJECTED", "REGISTRY_CHECK_PENDING"},
    "MORE_INFORMATION_REQUIRED": {"RESUBMITTED", "REJECTED"},
    "RESUBMITTED": {"REGISTRY_CHECK_PENDING", "UNDER_REVIEW"},
    "APPROVED": {"ADMIN_ACTIVATION_PENDING", "SETUP_REQUIRED"},
    "ADMIN_ACTIVATION_PENDING": {"SETUP_REQUIRED", "REJECTED"},
    "SETUP_REQUIRED": {"READINESS_REVIEW", "SUSPENDED"},
    "READINESS_REVIEW": {"ACTIVE", "SETUP_REQUIRED", "SUSPENDED"},
    "ACTIVE": {"SUSPENDED", "REVOKED"},
    "SUSPENDED": {"ACTIVE", "REVOKED"},
    "REVOKED": set(),
    "REJECTED": {"RESUBMITTED"},
}


def transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def transition_case(case, target: str, *, now: datetime | None = None) -> None:
    if target not in FACILITY_VERIFICATION_STATES:
        raise ValueError(f"Unknown facility verification state: {target}")
    if not transition_allowed(case.status, target):
        raise ValueError(f"Invalid facility verification transition: {case.status} -> {target}")
    case.status = target
    case.last_transition_at = now or datetime.now(UTC)
    if target in {"ACTIVE", "REJECTED", "REVOKED"}:
        case.resolved_at = case.last_transition_at


def review_due_at(submitted_at: datetime, *, business_days: int = 2) -> datetime:
    """Return a simple weekday SLA deadline; country-specific holidays can extend this later."""
    current = submitted_at.astimezone(UTC)
    remaining = business_days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current
