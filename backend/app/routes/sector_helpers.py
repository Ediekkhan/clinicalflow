from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AllergyRecord,
    AuthAccount,
    Benefit,
    ClaimAppeal,
    ClaimItem,
    ClaimResponse,
    ClinicalObservation,
    ClinicalPrivilege,
    ClinicalTask,
    ControlledMedicationLog,
    CountryPack,
    DataDisclosure,
    DenialReason,
    DispenseEvent,
    EligibilityRequest,
    EligibilityResponse,
    FacilityRegistry,
    GovernmentUserScope,
    HealthPlan,
    InsuranceClaim,
    InteractionAlert,
    InteroperabilityMapping,
    InventoryItem,
    MandatoryDiseaseReport,
    Medication,
    MedicationHistory,
    MemberCoverage,
    Notification,
    OfflineClinicalMutation,
    OutboxEvent,
    PatientCounselling,
    PayerOrganization,
    PharmacyDelivery,
    PharmacyOrder,
    Prescription,
    PrescriptionItem,
    PriorAuthorization,
    ProviderContract,
    Remittance,
    StaffMembership,
    StockMovement,
    SubstitutionRequest,
    SupportAccessApproval,
    SupportAccessRequest,
    SurveillanceAggregate,
    Tenant,
)
from app.routes.dependencies import (
    get_db,
    require_account,
    require_roles,
    require_staff_workspace,
)
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import utc_now
from app.services.country_policy import country_policy, nested_policy


def parse_uuid(value: Any, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422, detail=f"A valid {label} is required"
        ) from error


def parse_datetime(value: Any, label: str):
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422, detail=f"A valid {label} is required"
        ) from error


def is_expired(value) -> bool:
    if value is None:
        return False
    comparable = value if value.tzinfo else value.replace(tzinfo=utc_now().tzinfo)
    return comparable <= utc_now()


async def audit(
    session: AsyncSession,
    request: Request,
    account: AuthAccount,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
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


def notification(
    tenant_id: uuid.UUID,
    recipient: AuthAccount,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, Any],
) -> tuple[Notification, OutboxEvent]:
    notification_id = uuid.uuid4()
    row = Notification(
        id=notification_id,
        tenant_id=tenant_id,
        hospital_id=tenant_id,
        recipient_user_id=recipient.id,
        recipient_account_id=recipient.id,
        recipient_role=recipient.role,
        event_type=event_type,
        title=title,
        body=body,
        payload_json=json.dumps(payload),
    )
    event = OutboxEvent(
        tenant_id=tenant_id,
        aggregate_type="Notification",
        aggregate_id=notification_id,
        event_type=event_type.lower().replace("_", "."),
        recipient_user_id=recipient.id,
        payload_json=json.dumps(payload),
        classification="RESTRICTED",
    )
    return row, event


async def require_pharmacy(request: Request, session: AsyncSession) -> AuthAccount:
    account = await require_account(request, session)
    tenant = await session.get(Tenant, account.tenant_id)
    registry = await session.scalar(
        select(FacilityRegistry).where(
            FacilityRegistry.tenant_id == account.tenant_id,
            FacilityRegistry.facility_type == "PHARMACY",
            FacilityRegistry.status == "ACTIVE",
        )
    )
    if (
        account.role not in {"admin", "pharmacy", "pharmacist"}
        or not tenant
        or tenant.status != "ACTIVE"
        or not registry
    ):
        raise HTTPException(
            status_code=403, detail="An active pharmacy workspace is required"
        )
    return account


async def require_payer(
    request: Request, session: AsyncSession
) -> tuple[AuthAccount, PayerOrganization]:
    account = await require_account(request, session)
    payer = await session.scalar(
        select(PayerOrganization).where(
            PayerOrganization.tenant_id == account.tenant_id,
            PayerOrganization.status == "ACTIVE",
        )
    )
    if account.role not in {"admin", "hmo", "payer"} or not payer:
        raise HTTPException(
            status_code=403, detail="An active payer workspace is required"
        )
    return account, payer


def order_json(
    order: PharmacyOrder, prescription: Prescription, patient: AuthAccount | None = None
) -> dict[str, Any]:
    return {
        "id": str(order.id),
        "prescription_id": str(prescription.id),
        "status": order.status,
        "patient": {
            "id": str(prescription.patient_id),
            "display_name": (
                f"{patient.first_name} {patient.last_name}".strip() if patient else ""
            ),
        },
        "prescriber_id": str(prescription.prescriber_id),
        "expires_at": prescription.expires_at,
        "created_at": order.created_at,
    }


async def government_scope(
    session: AsyncSession, account: AuthAccount, jurisdiction: str | None = None
) -> GovernmentUserScope:
    scopes = list(
        (
            await session.execute(
                select(GovernmentUserScope).where(
                    GovernmentUserScope.user_id == account.id,
                    GovernmentUserScope.status == "ACTIVE",
                )
            )
        )
        .scalars()
        .all()
    )
    scope = next(
        (
            value
            for value in scopes
            if not jurisdiction
            or jurisdiction == value.jurisdiction_code
            or jurisdiction.startswith(f"{value.jurisdiction_code}:")
        ),
        None,
    )
    if not scope:
        raise HTTPException(
            status_code=403, detail="Government jurisdiction access denied"
        )
    return scope


__all__ = [name for name in globals() if not name.startswith("__")]
