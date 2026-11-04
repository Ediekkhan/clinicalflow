from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Accession,
    AllergyRecord,
    Appointment,
    AuthAccount,
    CareTeam,
    CareTeamMember,
    ClinicalDocument,
    ClinicalNote,
    ClinicalObservation,
    ClinicalPrivilege,
    ConditionRecord,
    ConsentRecord,
    CriticalResultAcknowledgement,
    DiagnosticReport,
    Encounter,
    FacilityRegistry,
    FacilityService,
    LaboratoryOrder,
    LaboratoryResult,
    Notification,
    NotificationDelivery,
    OrderedTest,
    OutboxEvent,
    ProvenanceRecord,
    QualityControlReview,
    Referral,
    ResultCorrection,
    Specimen,
    SpecimenCollection,
    SpecimenCustodyEvent,
    StaffMembership,
    Tenant,
    TransferRequest,
)
from app.routes.dependencies import get_db, require_account, require_roles
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import utc_now

CLINICIAN_ROLES = {"doctor", "specialist"}
LAB_ROLES = {"admin", "laboratory", "lab_scientist", "lab_technician"}


def parse_uuid(value: Any, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422, detail=f"A valid {label} is required"
        ) from error


async def verified_membership(
    session: AsyncSession, account: AuthAccount, facility_id: uuid.UUID | None = None
) -> StaffMembership:
    now = utc_now()
    membership = await session.scalar(
        select(StaffMembership).where(
            StaffMembership.user_id == account.id,
            StaffMembership.hospital_id == (facility_id or account.tenant_id),
            StaffMembership.is_active.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
            StaffMembership.active_from <= now,
            or_(
                StaffMembership.active_until.is_(None),
                StaffMembership.active_until >= now,
            ),
        )
    )
    if not membership:
        raise HTTPException(
            status_code=403, detail="An active verified facility membership is required"
        )
    return membership


async def audit(
    session: AsyncSession,
    request: Request,
    account: AuthAccount,
    resource_type: str,
    resource_id: uuid.UUID,
    action: str,
    tenant_id: uuid.UUID,
) -> None:
    session.add(
        ProvenanceRecord(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            actor_account_id=account.id,
            source="API",
        )
    )
    await write_audit_log(
        session,
        AuditAction.PATIENT_RECORD_UPDATED,
        actor_id=str(account.id),
        actor_type=account.role.upper(),
        tenant_id=str(tenant_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type=resource_type,
        resource_id=str(resource_id),
        metadata={"domain_action": action},
    )


def referral_json(row: Referral) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "patient_id": str(row.patient_id),
        "origin_facility_id": str(row.origin_facility_id),
        "destination_facility_id": str(row.destination_facility_id),
        "required_capability": row.required_capability,
        "required_specialty": row.required_specialty,
        "urgency": row.urgency,
        "status": row.status,
        "decision_reason": row.decision_reason,
        "expires_at": row.expires_at,
        "created_at": row.created_at,
    }


def order_json(
    order: LaboratoryOrder, tests: list[OrderedTest] | None = None
) -> dict[str, Any]:
    return {
        "id": str(order.id),
        "patient_id": str(order.patient_id),
        "ordering_facility_id": str(order.ordering_facility_id),
        "laboratory_id": str(order.laboratory_id),
        "ordering_clinician_id": str(order.ordering_clinician_id),
        "priority": order.priority,
        "status": order.status,
        "created_at": order.created_at,
        "tests": [
            {
                "id": str(test.id),
                "test_code": test.test_code,
                "display": test.display,
                "loinc_code": test.loinc_code,
                "status": test.status,
            }
            for test in (tests or [])
        ],
    }


async def require_lab_access(
    request: Request, session: AsyncSession, order_id: uuid.UUID | None = None
) -> tuple[AuthAccount, LaboratoryOrder | None]:
    account = await require_roles(request, session, LAB_ROLES)
    order = (
        await session.scalar(
            select(LaboratoryOrder).where(
                LaboratoryOrder.id == order_id,
                LaboratoryOrder.laboratory_id == account.tenant_id,
            )
        )
        if order_id
        else None
    )
    if order_id and not order:
        raise HTTPException(
            status_code=404, detail="Laboratory order not found in this workspace"
        )
    return account, order


__all__ = [name for name in globals() if not name.startswith("__")]
