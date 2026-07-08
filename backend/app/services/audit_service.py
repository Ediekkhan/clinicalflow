from enum import Enum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditAction(str, Enum):
    PATIENT_SIGNUP = "PATIENT_SIGNUP"
    PATIENT_LOGIN = "PATIENT_LOGIN"
    PATIENT_LOGOUT = "PATIENT_LOGOUT"
    SPECIALIST_LOGIN = "SPECIALIST_LOGIN"
    STAFF_LOGIN = "STAFF_LOGIN"
    FAILED_LOGIN = "FAILED_LOGIN"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    PATIENT_RECORD_VIEWED = "PATIENT_RECORD_VIEWED"
    PATIENT_RECORD_UPDATED = "PATIENT_RECORD_UPDATED"
    TRIAGE_SUBMITTED = "TRIAGE_SUBMITTED"
    TRIAGE_RESULT_VIEWED = "TRIAGE_RESULT_VIEWED"
    TICKET_CREATED = "TICKET_CREATED"
    TICKET_ESCALATED = "TICKET_ESCALATED"
    TICKET_STATUS_CHANGED = "TICKET_STATUS_CHANGED"
    TICKET_ASSIGNED = "TICKET_ASSIGNED"
    APPOINTMENT_BOOKED = "APPOINTMENT_BOOKED"
    APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED"
    APPOINTMENT_COMPLETED = "APPOINTMENT_COMPLETED"
    STAFF_CREATED = "STAFF_CREATED"
    STAFF_DEACTIVATED = "STAFF_DEACTIVATED"
    TENANT_SETTINGS_CHANGED = "TENANT_SETTINGS_CHANGED"
    KILL_SWITCH_TOGGLED = "KILL_SWITCH_TOGGLED"
    DATA_EXPORTED = "DATA_EXPORTED"
    DATA_DELETION_REQUEST = "DATA_DELETION_REQUEST"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"


def _uuid_or_none(value: str | UUID | None) -> UUID | None:
    if value is None or isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


async def write_audit_log(
    db: AsyncSession,
    action: AuditAction,
    actor_id: str | None,
    actor_type: str,
    tenant_id: str | None,
    ip_address: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    user_agent: str | None = None,
) -> None:
    log_metadata = dict(metadata or {})
    actor_uuid = _uuid_or_none(actor_id)
    if actor_id and actor_uuid is None:
        log_metadata["actor_id_raw"] = actor_id

    log = AuditLog(
        action=action.value,
        actor_id=actor_uuid,
        actor_type=actor_type,
        tenant_id=_uuid_or_none(tenant_id),
        ip_address=ip_address,
        resource_type=resource_type,
        resource_id=_uuid_or_none(resource_id),
        log_metadata=log_metadata or None,
        user_agent=user_agent,
    )
    db.add(log)

