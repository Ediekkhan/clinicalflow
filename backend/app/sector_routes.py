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
from app.routes import get_db, require_account, require_roles, require_staff_workspace
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import utc_now
from app.services.country_policy import country_policy, nested_policy

router = APIRouter(prefix="/api/v1")


def parse_uuid(value: Any, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"A valid {label} is required") from error


def parse_datetime(value: Any, label: str):
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utc_now().tzinfo)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"A valid {label} is required") from error


def is_expired(value) -> bool:
    if value is None:
        return False
    comparable = value if value.tzinfo else value.replace(tzinfo=utc_now().tzinfo)
    return comparable <= utc_now()


async def audit(session: AsyncSession, request: Request, account: AuthAccount, action: str, resource_type: str, resource_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
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


def notification(tenant_id: uuid.UUID, recipient: AuthAccount, event_type: str, title: str, body: str, payload: dict[str, Any]) -> tuple[Notification, OutboxEvent]:
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
    registry = await session.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == account.tenant_id, FacilityRegistry.facility_type == "PHARMACY", FacilityRegistry.status == "ACTIVE"))
    if account.role not in {"admin", "pharmacy", "pharmacist"} or not tenant or tenant.status != "ACTIVE" or not registry:
        raise HTTPException(status_code=403, detail="An active pharmacy workspace is required")
    return account


async def require_payer(request: Request, session: AsyncSession) -> tuple[AuthAccount, PayerOrganization]:
    account = await require_account(request, session)
    payer = await session.scalar(select(PayerOrganization).where(PayerOrganization.tenant_id == account.tenant_id, PayerOrganization.status == "ACTIVE"))
    if account.role not in {"admin", "hmo", "payer"} or not payer:
        raise HTTPException(status_code=403, detail="An active payer workspace is required")
    return account, payer


def order_json(order: PharmacyOrder, prescription: Prescription, patient: AuthAccount | None = None) -> dict[str, Any]:
    return {
        "id": str(order.id),
        "prescription_id": str(prescription.id),
        "status": order.status,
        "patient": {"id": str(prescription.patient_id), "display_name": (f"{patient.first_name} {patient.last_name}".strip() if patient else "")},
        "prescriber_id": str(prescription.prescriber_id),
        "expires_at": prescription.expires_at,
        "created_at": order.created_at,
    }


@router.post("/pharmacy/medications", status_code=201)
async def create_medication(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    payload = await request.json()
    code, name = str(payload.get("code") or "").strip(), str(payload.get("generic_name") or "").strip()
    if not code or not name:
        raise HTTPException(status_code=422, detail="Medication code and generic name are required")
    row = Medication(country_code=str(payload.get("country_code") or "NG").upper(), code=code, generic_name=name, form=payload.get("form"), strength=payload.get("strength"), controlled_schedule=payload.get("controlled_schedule"))
    session.add(row)
    await session.flush()
    await audit(session, request, account, "CREATED", "Medication", row.id, account.tenant_id)
    await session.commit()
    return {"id": str(row.id), "code": row.code, "generic_name": row.generic_name, "controlled_schedule": row.controlled_schedule}


@router.post("/pharmacy/inventory", status_code=201)
async def create_inventory(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    payload = await request.json()
    medication_id = parse_uuid(payload.get("medication_id"), "medication_id")
    if not await session.get(Medication, medication_id):
        raise HTTPException(status_code=404, detail="Medication not found")
    quantity = int(payload.get("quantity_on_hand") or 0)
    if quantity < 0:
        raise HTTPException(status_code=422, detail="Inventory quantity cannot be negative")
    row = InventoryItem(pharmacy_id=account.tenant_id, medication_id=medication_id, batch_number=str(payload.get("batch_number") or "").strip(), quantity_on_hand=quantity, reorder_level=max(0, int(payload.get("reorder_level") or 0)), expires_at=parse_datetime(payload.get("expires_at"), "expires_at"))
    if not row.batch_number:
        raise HTTPException(status_code=422, detail="Batch number is required")
    session.add(row)
    await session.flush()
    session.add(StockMovement(inventory_item_id=row.id, movement_type="RECEIPT", quantity=quantity, actor_id=account.id))
    await session.commit()
    return {"id": str(row.id), "quantity_on_hand": row.quantity_on_hand, "status": row.status}


@router.post("/prescriptions", status_code=201)
async def create_prescription(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist"})
    membership = await require_staff_workspace(session, account, roles={"doctor", "specialist"})
    privilege = await session.scalar(select(ClinicalPrivilege).where(ClinicalPrivilege.membership_id == membership.id, ClinicalPrivilege.code == "PRESCRIBE", ClinicalPrivilege.status == "ACTIVE", ClinicalPrivilege.revoked_at.is_(None)))
    if not privilege:
        raise HTTPException(status_code=403, detail="Active prescribing privilege is required")
    payload = await request.json()
    patient_id, pharmacy_id = parse_uuid(payload.get("patient_id"), "patient_id"), parse_uuid(payload.get("pharmacy_id"), "pharmacy_id")
    patient = await session.scalar(select(AuthAccount).where(AuthAccount.id == patient_id, AuthAccount.role == "patient", AuthAccount.is_active.is_(True)))
    pharmacy = await session.scalar(select(Tenant).where(Tenant.id == pharmacy_id, Tenant.status == "ACTIVE"))
    items = payload.get("items")
    if not patient or not pharmacy or not isinstance(items, list) or not items:
        raise HTTPException(status_code=422, detail="An active patient, pharmacy, and at least one item are required")
    policy = await country_policy(session, str(payload.get("country_code") or "NG"))
    if account.role not in set(nested_policy(policy, "prescription", "allowed_prescriber_roles", default=[])):
        raise HTTPException(status_code=403, detail="This country policy does not permit the account role to prescribe")
    row = Prescription(patient_id=patient.id, encounter_id=parse_uuid(payload["encounter_id"], "encounter_id") if payload.get("encounter_id") else None, prescriber_id=account.id, prescriber_membership_id=membership.id, facility_id=membership.hospital_id, pharmacy_id=pharmacy.id, country_code=str(payload.get("country_code") or "NG").upper(), expires_at=utc_now() + timedelta(days=int(nested_policy(policy, "prescription", "default_valid_days", default=30))))
    session.add(row)
    await session.flush()
    for value in items:
        medication_id = parse_uuid(value.get("medication_id"), "medication_id")
        medication = await session.get(Medication, medication_id)
        quantity, days = int(value.get("quantity") or 0), int(value.get("duration_days") or 0)
        if not medication or medication.status != "ACTIVE" or quantity <= 0 or days <= 0 or not str(value.get("dosage") or "").strip() or not str(value.get("frequency") or "").strip():
            raise HTTPException(status_code=422, detail="Every prescription item requires an active medication, dosage, frequency, duration, and positive quantity")
        session.add(PrescriptionItem(prescription_id=row.id, medication_id=medication.id, dosage=str(value["dosage"]).strip(), route=value.get("route"), frequency=str(value["frequency"]).strip(), duration_days=days, quantity=quantity, substitution_allowed=bool(value.get("substitution_allowed", False))))
    order = PharmacyOrder(prescription_id=row.id, pharmacy_id=pharmacy.id)
    session.add(order)
    await session.flush()
    pharmacy_users = list((await session.execute(select(AuthAccount).where(AuthAccount.tenant_id == pharmacy.id, AuthAccount.role.in_(["admin", "pharmacy", "pharmacist"]), AuthAccount.is_active.is_(True)))).scalars().all())
    for recipient in pharmacy_users:
        session.add_all(notification(pharmacy.id, recipient, "PRESCRIPTION_RECEIVED", "Prescription received", "A signed prescription is ready for pharmacy validation.", {"order_id": str(order.id)}))
    await audit(session, request, account, "SIGNED", "Prescription", row.id, membership.hospital_id)
    await session.commit()
    return {"id": str(row.id), "order_id": str(order.id), "status": row.status, "expires_at": row.expires_at}


@router.get("/pharmacy/prescriptions")
async def list_pharmacy_orders(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_pharmacy(request, session)
    rows = list((await session.execute(select(PharmacyOrder, Prescription, AuthAccount).join(Prescription, Prescription.id == PharmacyOrder.prescription_id).join(AuthAccount, AuthAccount.id == Prescription.patient_id).where(PharmacyOrder.pharmacy_id == account.tenant_id).order_by(PharmacyOrder.created_at.desc()).limit(200))).all())
    return [order_json(order, prescription, patient) for order, prescription, patient in rows]


@router.get("/pharmacy/inventory")
async def list_inventory(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_pharmacy(request, session)
    rows = list((await session.execute(select(InventoryItem, Medication).join(Medication, Medication.id == InventoryItem.medication_id).where(InventoryItem.pharmacy_id == account.tenant_id).order_by(InventoryItem.expires_at))).all())
    return [{"id": str(row.id), "medication": medication.generic_name, "batch_number": row.batch_number, "quantity_on_hand": row.quantity_on_hand, "reorder_level": row.reorder_level, "expires_at": row.expires_at, "low_stock": row.quantity_on_hand <= row.reorder_level, "status": row.status} for row, medication in rows]


@router.get("/pharmacy/dashboard")
async def pharmacy_dashboard(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    pending = await session.scalar(select(func.count()).select_from(PharmacyOrder).where(PharmacyOrder.pharmacy_id == account.tenant_id, PharmacyOrder.status.in_(["RECEIVED", "VALIDATED", "PARTIALLY_DISPENSED"])))
    low = await session.scalar(select(func.count()).select_from(InventoryItem).where(InventoryItem.pharmacy_id == account.tenant_id, InventoryItem.quantity_on_hand <= InventoryItem.reorder_level))
    return {"stats": {"pending_prescriptions": pending, "low_stock_items": low}, "recent": await list_pharmacy_orders(request, session)}


@router.post("/pharmacy/orders/{order_id}/validate")
async def validate_order(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    order = await session.scalar(select(PharmacyOrder).where(PharmacyOrder.id == parse_uuid(order_id, "order_id"), PharmacyOrder.pharmacy_id == account.tenant_id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="Pharmacy order not found")
    prescription = await session.get(Prescription, order.prescription_id)
    if not prescription or is_expired(prescription.expires_at):
        order.status = "EXPIRED"
        await session.commit()
        raise HTTPException(status_code=409, detail="Prescription has expired")
    alerts = await session.scalar(select(func.count()).select_from(InteractionAlert).where(InteractionAlert.prescription_id == prescription.id, InteractionAlert.severity == "CRITICAL", InteractionAlert.acknowledged_at.is_(None)))
    if alerts:
        raise HTTPException(status_code=409, detail="Critical interaction alerts must be acknowledged before validation")
    payload = await request.json()
    order.status, order.validated_by_id, order.validation_notes, order.validated_at = "VALIDATED", account.id, str(payload.get("notes") or "").strip() or None, utc_now()
    await session.commit()
    return {"id": str(order.id), "status": order.status}


@router.post("/pharmacy/orders/{order_id}/dispense")
async def dispense_order(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    key = str(request.headers.get("x-idempotency-key") or "").strip()
    if not key:
        raise HTTPException(status_code=422, detail="X-Idempotency-Key is required")
    payload = await request.json()
    item_id, inventory_id = parse_uuid(payload.get("prescription_item_id"), "prescription_item_id"), parse_uuid(payload.get("inventory_item_id"), "inventory_item_id")
    existing = await session.scalar(select(DispenseEvent).where(DispenseEvent.prescription_item_id == item_id, DispenseEvent.idempotency_key == key))
    if existing:
        return {"id": str(existing.id), "status": "ALREADY_PROCESSED", "quantity": existing.quantity}
    order = await session.scalar(select(PharmacyOrder).where(PharmacyOrder.id == parse_uuid(order_id, "order_id"), PharmacyOrder.pharmacy_id == account.tenant_id).with_for_update())
    if not order or order.status not in {"VALIDATED", "PARTIALLY_DISPENSED"}:
        raise HTTPException(status_code=409, detail="A validated pharmacy order is required")
    prescription = await session.get(Prescription, order.prescription_id)
    item = await session.scalar(select(PrescriptionItem).where(PrescriptionItem.id == item_id, PrescriptionItem.prescription_id == order.prescription_id).with_for_update())
    inventory = await session.scalar(select(InventoryItem).where(InventoryItem.id == inventory_id, InventoryItem.pharmacy_id == account.tenant_id).with_for_update())
    medication = await session.get(Medication, item.medication_id) if item else None
    quantity = int(payload.get("quantity") or 0)
    if not prescription or is_expired(prescription.expires_at) or not item or not inventory or inventory.medication_id != item.medication_id:
        raise HTTPException(status_code=422, detail="Prescription item and matching pharmacy inventory are required")
    remaining = item.quantity - item.quantity_dispensed
    if quantity <= 0 or quantity > remaining or quantity > inventory.quantity_on_hand or is_expired(inventory.expires_at):
        raise HTTPException(status_code=409, detail="Requested quantity is unavailable, expired, or exceeds the prescription")
    if medication and medication.controlled_schedule and (not payload.get("witness_id") or not str(payload.get("register_reference") or "").strip()):
        raise HTTPException(status_code=422, detail="Controlled medicine dispensing requires a witness and register reference")
    event = DispenseEvent(pharmacy_order_id=order.id, prescription_item_id=item.id, inventory_item_id=inventory.id, quantity=quantity, dispenser_id=account.id, idempotency_key=key)
    session.add(event)
    await session.flush()
    item.quantity_dispensed += quantity
    item.status = "DISPENSED" if item.quantity_dispensed == item.quantity else "PARTIALLY_DISPENSED"
    inventory.quantity_on_hand -= quantity
    inventory.status = "LOW_STOCK" if inventory.quantity_on_hand <= inventory.reorder_level else "AVAILABLE"
    session.add(StockMovement(inventory_item_id=inventory.id, movement_type="DISPENSE", quantity=-quantity, reference_type="DispenseEvent", reference_id=event.id, actor_id=account.id))
    if medication and medication.controlled_schedule:
        session.add(ControlledMedicationLog(dispense_event_id=event.id, schedule=medication.controlled_schedule, witness_id=parse_uuid(payload.get("witness_id"), "witness_id"), register_reference=str(payload["register_reference"]).strip()))
    open_items = await session.scalar(select(func.count()).select_from(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id, PrescriptionItem.id != item.id, PrescriptionItem.status != "DISPENSED"))
    order.status = "DISPENSED" if item.status == "DISPENSED" and not open_items else "PARTIALLY_DISPENSED"
    if order.status == "DISPENSED":
        prescription.status = "DISPENSED"
    session.add(MedicationHistory(patient_id=prescription.patient_id, encounter_id=prescription.encounter_id, medication_name=medication.generic_name if medication else "Medication", dosage=item.dosage, status="DISPENSED", started_at=utc_now()))
    patient = await session.get(AuthAccount, prescription.patient_id)
    if patient:
        session.add_all(notification(account.tenant_id, patient, "PRESCRIPTION_DISPENSED", "Prescription update", "Your prescription dispensing status has changed.", {"order_id": str(order.id), "status": order.status}))
    await audit(session, request, account, "DISPENSED", "PharmacyOrder", order.id, account.tenant_id)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="This dispensing action was already processed") from error
    return {"id": str(event.id), "status": order.status, "quantity": quantity}


@router.post("/pharmacy/orders/{order_id}/counselling", status_code=201)
async def record_counselling(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_pharmacy(request, session)
    order = await session.scalar(select(PharmacyOrder).where(PharmacyOrder.id == parse_uuid(order_id, "order_id"), PharmacyOrder.pharmacy_id == account.tenant_id))
    payload = await request.json()
    topics = payload.get("topics")
    if not order or not isinstance(topics, list) or not topics:
        raise HTTPException(status_code=422, detail="A pharmacy order and counselling topics are required")
    row = PatientCounselling(pharmacy_order_id=order.id, pharmacist_id=account.id, topics_json=json.dumps(topics), patient_understood=bool(payload.get("patient_understood")), notes=str(payload.get("notes") or "").strip() or None)
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "patient_understood": row.patient_understood}


@router.post("/coverage/eligibility", status_code=201)
async def check_eligibility(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    payload = await request.json()
    patient_id = account.id if account.role == "patient" else parse_uuid(payload.get("patient_id"), "patient_id")
    facility_id = account.tenant_id if account.role != "patient" else parse_uuid(payload.get("facility_id"), "facility_id")
    service_code, lawful_basis = str(payload.get("service_code") or "").strip(), str(payload.get("lawful_basis") or "").strip()
    if not service_code or not lawful_basis:
        raise HTTPException(status_code=422, detail="Service code and lawful basis are required")
    now, emergency = utc_now(), bool(payload.get("emergency"))
    coverages = list((await session.execute(select(MemberCoverage).where(MemberCoverage.patient_id == patient_id, MemberCoverage.status == "ACTIVE", MemberCoverage.starts_at <= now, or_(MemberCoverage.ends_at.is_(None), MemberCoverage.ends_at >= now)).order_by(MemberCoverage.starts_at.desc()))).scalars().all())
    requested_coverage = parse_uuid(payload["coverage_id"], "coverage_id") if payload.get("coverage_id") else None
    coverage = next((item for item in coverages if not requested_coverage or item.id == requested_coverage), None)
    payer_id = coverage.payer_id if coverage else None
    row = EligibilityRequest(patient_id=patient_id, facility_id=facility_id, payer_id=payer_id, coverage_id=coverage.id if coverage else None, service_code=service_code, emergency=emergency, lawful_basis=lawful_basis, requested_by_id=account.id)
    session.add(row)
    await session.flush()
    eligible, reason, currency = False, "No active coverage found; self-pay remains available.", "NGN"
    if coverage:
        plan = await session.get(HealthPlan, coverage.plan_id)
        contract = await session.scalar(select(ProviderContract).where(ProviderContract.payer_id == coverage.payer_id, ProviderContract.facility_id == facility_id, ProviderContract.status == "ACTIVE", ProviderContract.starts_at <= now, or_(ProviderContract.ends_at.is_(None), ProviderContract.ends_at >= now)))
        benefit = await session.scalar(select(Benefit).where(Benefit.plan_id == coverage.plan_id, Benefit.service_code == service_code))
        eligible = bool(plan and plan.status == "ACTIVE" and contract and benefit)
        reason, currency = ("Coverage and provider contract are active." if eligible else "The service or provider contract is not covered."), plan.currency if plan else "NGN"
    if emergency and not eligible:
        reason += " Emergency care must not be delayed for authorization."
    response = EligibilityResponse(request_id=row.id, eligible=eligible, reason=reason, currency=currency)
    session.add(response)
    await session.commit()
    return {"request_id": str(row.id), "eligible": eligible, "reason": reason, "coverage_id": str(coverage.id) if coverage else None, "self_pay_available": not eligible, "care_must_continue": emergency}


@router.get("/patients/me/coverage")
async def my_coverage(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_roles(request, session, {"patient"})
    rows = list((await session.execute(select(MemberCoverage, HealthPlan, PayerOrganization).join(HealthPlan, HealthPlan.id == MemberCoverage.plan_id).join(PayerOrganization, PayerOrganization.id == MemberCoverage.payer_id).where(MemberCoverage.patient_id == account.id).order_by(MemberCoverage.starts_at.desc()))).all())
    return [{"id": str(row.id), "payer": payer.legal_name, "plan": plan.name, "member_number": row.member_number, "status": row.status, "starts_at": row.starts_at, "ends_at": row.ends_at} for row, plan, payer in rows]


@router.post("/authorizations", status_code=201)
async def create_authorization(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    payload = await request.json()
    coverage = await session.get(MemberCoverage, parse_uuid(payload.get("coverage_id"), "coverage_id"))
    service_code = str(payload.get("service_code") or "").strip()
    if not coverage or not service_code:
        raise HTTPException(status_code=422, detail="Active coverage and service code are required")
    if account.role == "patient" and coverage.patient_id != account.id:
        raise HTTPException(status_code=403, detail="Coverage access denied")
    row = PriorAuthorization(coverage_id=coverage.id, facility_id=account.tenant_id, service_code=service_code, minimum_clinical_summary=str(payload.get("minimum_clinical_summary") or "").strip() or None, emergency=bool(payload.get("emergency")))
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status, "emergency_care_must_continue": row.emergency}


@router.patch("/hmo/authorizations/{authorization_id}/decision")
async def decide_authorization(authorization_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, payer = await require_payer(request, session)
    row = await session.scalar(select(PriorAuthorization).join(MemberCoverage, MemberCoverage.id == PriorAuthorization.coverage_id).where(PriorAuthorization.id == parse_uuid(authorization_id, "authorization_id"), MemberCoverage.payer_id == payer.id).with_for_update())
    payload = await request.json()
    decision, reason = str(payload.get("decision") or "").upper(), str(payload.get("reason") or "").strip()
    if not row:
        raise HTTPException(status_code=404, detail="Authorization not found")
    if decision not in {"APPROVED", "DENIED"} or len(reason) < 3:
        raise HTTPException(status_code=422, detail="APPROVED or DENIED decision and a reason are required")
    row.status, row.reason, row.decided_by_id, row.decided_at = decision, reason, account.id, utc_now()
    await session.commit()
    return {"id": str(row.id), "status": row.status, "reason": row.reason, "emergency_care_must_continue": row.emergency}


@router.post("/claims", status_code=201)
async def submit_claim(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role == "patient":
        raise HTTPException(status_code=403, detail="Claims must be submitted by an authorized facility")
    payload = await request.json()
    coverage = await session.get(MemberCoverage, parse_uuid(payload.get("coverage_id"), "coverage_id"))
    items = payload.get("items")
    reference, lawful_basis = str(payload.get("external_reference") or "").strip(), str(payload.get("lawful_basis") or "").strip()
    if not coverage or not reference or not lawful_basis or not isinstance(items, list) or not items:
        raise HTTPException(status_code=422, detail="Coverage, unique reference, lawful basis, and claim items are required")
    if await session.scalar(select(InsuranceClaim.id).where(InsuranceClaim.payer_id == coverage.payer_id, InsuranceClaim.external_reference == reference)):
        raise HTTPException(status_code=409, detail="Duplicate claim reference")
    values = []
    for value in items:
        amount, quantity = int(value.get("amount_minor") or 0), int(value.get("quantity") or 1)
        if not str(value.get("service_code") or "").strip() or amount <= 0 or quantity <= 0:
            raise HTTPException(status_code=422, detail="Every claim item requires a service code, positive amount, and quantity")
        values.append((str(value["service_code"]).strip(), amount, quantity))
    row = InsuranceClaim(payer_id=coverage.payer_id, coverage_id=coverage.id, facility_id=account.tenant_id, patient_id=coverage.patient_id, external_reference=reference, total_minor=sum(amount * quantity for _, amount, quantity in values), currency=str(payload.get("currency") or "NGN").upper(), lawful_basis=lawful_basis)
    session.add(row)
    await session.flush()
    session.add_all([ClaimItem(claim_id=row.id, service_code=code, amount_minor=amount, quantity=quantity) for code, amount, quantity in values])
    await session.commit()
    return {"id": str(row.id), "status": row.status, "total_minor": row.total_minor, "currency": row.currency}


@router.patch("/hmo/claims/{claim_id}/decision")
async def decide_claim(claim_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, payer = await require_payer(request, session)
    row = await session.scalar(select(InsuranceClaim).where(InsuranceClaim.id == parse_uuid(claim_id, "claim_id"), InsuranceClaim.payer_id == payer.id).with_for_update())
    payload = await request.json()
    decision, reason = str(payload.get("decision") or "").upper(), str(payload.get("reason") or "").strip()
    if not row:
        raise HTTPException(status_code=404, detail="Claim not found")
    if decision not in {"APPROVED", "PARTIALLY_APPROVED", "DENIED"} or len(reason) < 3:
        raise HTTPException(status_code=422, detail="A supported decision and reason are required")
    approved = int(payload.get("approved_minor") or 0)
    if approved < 0 or approved > row.total_minor or (decision == "APPROVED" and approved != row.total_minor):
        raise HTTPException(status_code=422, detail="Approved amount is inconsistent with the decision")
    if await session.scalar(select(ClaimResponse.id).where(ClaimResponse.claim_id == row.id)):
        raise HTTPException(status_code=409, detail="Claim has already been decided")
    response = ClaimResponse(claim_id=row.id, decision=decision, approved_minor=approved, reason=reason, decided_by_id=account.id)
    session.add(response)
    row.status = decision
    await session.commit()
    return {"id": str(row.id), "status": row.status, "approved_minor": approved, "reason": reason}


@router.post("/claims/{claim_id}/appeals", status_code=201)
async def appeal_claim(claim_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    row = await session.get(InsuranceClaim, parse_uuid(claim_id, "claim_id"))
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    if not row or row.facility_id != account.tenant_id or row.status not in {"DENIED", "PARTIALLY_APPROVED"} or len(reason) < 5:
        raise HTTPException(status_code=422, detail="A denied facility claim and appeal reason are required")
    appeal = ClaimAppeal(claim_id=row.id, submitted_by_id=account.id, reason=reason)
    session.add(appeal)
    await session.commit()
    return {"id": str(appeal.id), "status": appeal.status}


@router.get("/hmo/{resource}")
async def hmo_resource(resource: str, request: Request, session: AsyncSession = Depends(get_db)) -> Any:
    account, payer = await require_payer(request, session)
    if resource == "dashboard":
        claims = await session.scalar(select(func.count()).select_from(InsuranceClaim).where(InsuranceClaim.payer_id == payer.id))
        members = await session.scalar(select(func.count()).select_from(MemberCoverage).where(MemberCoverage.payer_id == payer.id, MemberCoverage.status == "ACTIVE"))
        pending = await session.scalar(select(func.count()).select_from(PriorAuthorization).join(MemberCoverage, MemberCoverage.id == PriorAuthorization.coverage_id).where(MemberCoverage.payer_id == payer.id, PriorAuthorization.status == "REQUESTED"))
        return {"stats": {"claims": claims, "members": members, "pending_authorizations": pending}}
    if resource == "members":
        rows = list((await session.execute(select(MemberCoverage).where(MemberCoverage.payer_id == payer.id).order_by(MemberCoverage.starts_at.desc()).limit(200))).scalars().all())
        return [{"id": str(row.id), "patient_id": str(row.patient_id), "member_number": row.member_number, "status": row.status, "starts_at": row.starts_at, "ends_at": row.ends_at} for row in rows]
    if resource == "claims":
        rows = list((await session.execute(select(InsuranceClaim).where(InsuranceClaim.payer_id == payer.id).order_by(InsuranceClaim.submitted_at.desc()).limit(200))).scalars().all())
        return [{"id": str(row.id), "external_reference": row.external_reference, "status": row.status, "total_minor": row.total_minor, "currency": row.currency, "submitted_at": row.submitted_at} for row in rows]
    if resource == "authorizations":
        rows = list((await session.execute(select(PriorAuthorization).join(MemberCoverage, MemberCoverage.id == PriorAuthorization.coverage_id).where(MemberCoverage.payer_id == payer.id).order_by(PriorAuthorization.created_at.desc()).limit(200))).scalars().all())
        return [{"id": str(row.id), "service_code": row.service_code, "status": row.status, "emergency": row.emergency, "reason": row.reason, "created_at": row.created_at} for row in rows]
    if resource in {"analytics", "utilization", "payments", "facilities"}:
        return []
    raise HTTPException(status_code=404, detail="Payer resource not found")


async def government_scope(session: AsyncSession, account: AuthAccount, jurisdiction: str | None = None) -> GovernmentUserScope:
    scopes = list((await session.execute(select(GovernmentUserScope).where(GovernmentUserScope.user_id == account.id, GovernmentUserScope.status == "ACTIVE"))).scalars().all())
    scope = next((value for value in scopes if not jurisdiction or jurisdiction == value.jurisdiction_code or jurisdiction.startswith(f"{value.jurisdiction_code}:")), None)
    if not scope:
        raise HTTPException(status_code=403, detail="Government jurisdiction access denied")
    return scope


@router.get("/moh/{resource}")
async def government_resource(resource: str, request: Request, jurisdiction: str | None = None, session: AsyncSession = Depends(get_db)) -> Any:
    account = await require_account(request, session)
    scope = await government_scope(session, account, jurisdiction)
    prefix = jurisdiction or scope.jurisdiction_code
    if resource == "dashboard":
        reports = await session.scalar(select(func.count()).select_from(MandatoryDiseaseReport).where(MandatoryDiseaseReport.jurisdiction_code.like(f"{prefix}%")))
        alerts = 0
        return {"stats": {"submitted_reports": reports, "active_alerts": alerts}, "jurisdiction": prefix, "data_mode": "AGGREGATE"}
    if resource in {"reports", "surveillance"}:
        threshold = int(nested_policy(await country_policy(session), "mandatory_reporting", "small_cell_suppression", default=5))
        rows = list((await session.execute(select(MandatoryDiseaseReport).where(MandatoryDiseaseReport.jurisdiction_code.like(f"{prefix}%")).order_by(MandatoryDiseaseReport.submitted_at.desc()).limit(200))).scalars().all())
        return [{"id": str(row.id), "jurisdiction_code": row.jurisdiction_code, "report_type": row.report_type, "condition_code": row.condition_code, "reporting_period": row.reporting_period, "aggregate_count": None if row.aggregate_count < threshold else row.aggregate_count, "suppressed": row.aggregate_count < threshold, "submitted_at": row.submitted_at} for row in rows]
    if resource in {"facilities", "hospitals"}:
        rows = list((await session.execute(select(Tenant).where(Tenant.status == "ACTIVE").order_by(Tenant.name).limit(200))).scalars().all())
        return [{"id": str(row.id), "name": row.name, "location": row.state_location, "status": row.status} for row in rows]
    if resource == "settings":
        return {"jurisdiction": prefix, "identifiable_reporting_allowed": scope.identifiable_reporting_allowed}
    raise HTTPException(status_code=404, detail="Government resource not found")


@router.post("/moh/reports", status_code=201)
async def submit_disease_report(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role in {"government", "moh"}:
        raise HTTPException(status_code=403, detail="Reports must be submitted by an authorized facility")
    payload = await request.json()
    identifiable = payload.get("identifiable_payload")
    legal_reference = str(payload.get("legal_authority_reference") or "").strip() or None
    if identifiable and not legal_reference:
        raise HTTPException(status_code=422, detail="Identifiable reporting requires a legal authority reference")
    row = MandatoryDiseaseReport(facility_id=account.tenant_id, jurisdiction_code=str(payload.get("jurisdiction_code") or "").strip(), report_type=str(payload.get("report_type") or "").strip(), condition_code=str(payload.get("condition_code") or "").strip(), reporting_period=str(payload.get("reporting_period") or "").strip(), aggregate_count=max(0, int(payload.get("aggregate_count") or 0)), identifiable_payload_json=json.dumps(identifiable) if identifiable else None, legal_authority_reference=legal_reference, submitted_by_id=account.id)
    if not all((row.jurisdiction_code, row.report_type, row.condition_code, row.reporting_period)):
        raise HTTPException(status_code=422, detail="Jurisdiction, report type, condition code, and reporting period are required")
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": "SUBMITTED", "contains_identifiable_data": bool(identifiable)}


@router.get("/moh/reports/{report_id}/identifiable")
async def read_identifiable_report(report_id: str, request: Request, legal_basis: str, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    row = await session.get(MandatoryDiseaseReport, parse_uuid(report_id, "report_id"))
    scope = await government_scope(session, account, row.jurisdiction_code if row else None)
    if not row or not row.identifiable_payload_json:
        raise HTTPException(status_code=404, detail="Identifiable report not found")
    if not scope.identifiable_reporting_allowed or not row.legal_authority_reference or len(legal_basis.strip()) < 5:
        raise HTTPException(status_code=403, detail="Configured legal authority and an access basis are required")
    disclosure = DataDisclosure(government_user_id=account.id, report_id=row.id, disclosure_type="MANDATORY_DISEASE_REPORT", legal_basis=legal_basis.strip(), fields_json=json.dumps(list(json.loads(row.identifiable_payload_json).keys())))
    session.add(disclosure)
    await session.commit()
    return {"id": str(row.id), "payload": json.loads(row.identifiable_payload_json), "disclosure_id": str(disclosure.id)}


@router.post("/platform/support-access", status_code=201)
async def request_support_access(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    hours = max(1, min(int(payload.get("hours") or 1), 8))
    if len(reason) < 10:
        raise HTTPException(status_code=422, detail="A specific support reason is required")
    row = SupportAccessRequest(requester_id=account.id, facility_id=parse_uuid(payload.get("facility_id"), "facility_id"), reason=reason, sensitive_access=bool(payload.get("sensitive_access", True)), expires_at=utc_now() + timedelta(hours=hours))
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status, "expires_at": row.expires_at}


@router.post("/platform/support-access/{request_id}/approvals", status_code=201)
async def approve_support_access(request_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    row = await session.scalar(select(SupportAccessRequest).where(SupportAccessRequest.id == parse_uuid(request_id, "request_id")).with_for_update())
    if not row or row.status not in {"PENDING", "APPROVED"} or is_expired(row.expires_at):
        raise HTTPException(status_code=409, detail="Support access request is not open")
    await require_staff_workspace(session, account, hospital_id=row.facility_id, roles={"hospital_admin", "department_coordinator"})
    payload = await request.json()
    decision, reason = str(payload.get("decision") or "").upper(), str(payload.get("reason") or "").strip()
    if decision not in {"APPROVED", "DENIED"} or len(reason) < 3:
        raise HTTPException(status_code=422, detail="Approval decision and reason are required")
    session.add(SupportAccessApproval(request_id=row.id, approver_id=account.id, decision=decision, reason=reason))
    await session.flush()
    approvals = await session.scalar(select(func.count()).select_from(SupportAccessApproval).where(SupportAccessApproval.request_id == row.id, SupportAccessApproval.decision == "APPROVED"))
    if decision == "DENIED":
        row.status = "DENIED"
    elif approvals >= (2 if row.sensitive_access else 1):
        row.status, row.activated_at = "ACTIVE", utc_now()
    await session.commit()
    return {"id": str(row.id), "status": row.status, "approvals": approvals, "expires_at": row.expires_at}


@router.get("/country-packs/{country_code}/active")
async def active_country_pack(country_code: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await require_account(request, session)
    code = country_code.upper()
    row = await session.scalar(select(CountryPack).where(CountryPack.country_code == code, CountryPack.status == "ACTIVE").order_by(CountryPack.effective_from.desc(), CountryPack.created_at.desc()))
    if not row and code == "NG":
        await country_policy(session, code)
        row = await session.scalar(select(CountryPack).where(CountryPack.country_code == code, CountryPack.status == "ACTIVE").order_by(CountryPack.created_at.desc()))
    if not row:
        raise HTTPException(status_code=404, detail="No active country pack")
    return {"country_code": row.country_code, "version": row.version, "policy": json.loads(row.policy_json), "requires_legal_review": row.requires_legal_review, "reviewed_by": row.reviewed_by}


@router.get("/interoperability/mappings")
async def interoperability_mappings(request: Request, country_code: str = "NG", session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    await require_account(request, session)
    rows = list((await session.execute(select(InteroperabilityMapping).join(CountryPack, CountryPack.id == InteroperabilityMapping.country_pack_id).where(CountryPack.country_code == country_code.upper(), CountryPack.status == "ACTIVE", InteroperabilityMapping.status == "ACTIVE").order_by(InteroperabilityMapping.resource_type))).scalars().all())
    return [{"resource_type": row.resource_type, "standard": row.standard, "version": row.version, "mapping": json.loads(row.mapping_json)} for row in rows]


@router.post("/offline/mutations", status_code=202)
async def enqueue_offline_mutation(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    payload = await request.json()
    client_id, mutation_type = str(payload.get("client_mutation_id") or "").strip(), str(payload.get("mutation_type") or "").upper()
    body = payload.get("payload")
    if not client_id or mutation_type not in {"CLINICAL_TASK", "OBSERVATION"} or not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Client mutation ID, supported mutation type, and payload are required")
    existing = await session.scalar(select(OfflineClinicalMutation).where(OfflineClinicalMutation.account_id == account.id, OfflineClinicalMutation.client_mutation_id == client_id))
    if existing:
        return {"id": str(existing.id), "status": existing.status, "duplicate": True}
    row = OfflineClinicalMutation(account_id=account.id, tenant_id=account.tenant_id, client_mutation_id=client_id, mutation_type=mutation_type, payload_json=json.dumps(body))
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status, "duplicate": False}


@router.post("/offline/mutations/sync")
async def sync_offline_mutations(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    await require_staff_workspace(session, account)
    rows = list((await session.execute(select(OfflineClinicalMutation).where(OfflineClinicalMutation.account_id == account.id, OfflineClinicalMutation.status.in_(["PENDING", "FAILED"])).order_by(OfflineClinicalMutation.created_at).limit(100).with_for_update())).scalars().all())
    synced, failed = 0, 0
    for row in rows:
        row.attempts += 1
        try:
            body = json.loads(row.payload_json)
            patient_id = parse_uuid(body.get("patient_id"), "patient_id")
            if row.mutation_type == "CLINICAL_TASK":
                description = str(body.get("description") or "").strip()
                if not description:
                    raise ValueError("Task description is required")
                session.add(ClinicalTask(patient_id=patient_id, facility_id=account.tenant_id, assignee_id=parse_uuid(body["assignee_id"], "assignee_id") if body.get("assignee_id") else None, task_type=str(body.get("task_type") or "FOLLOW_UP"), description=description, due_at=parse_datetime(body["due_at"], "due_at") if body.get("due_at") else None))
            else:
                if not all(str(body.get(key) or "").strip() for key in ("code", "display", "value")):
                    raise ValueError("Observation code, display, and value are required")
                session.add(ClinicalObservation(patient_id=patient_id, code=str(body["code"]), display=str(body["display"]), value=str(body["value"]), unit=body.get("unit"), abnormal_flag=body.get("abnormal_flag"), observed_by_id=account.id, observed_at=parse_datetime(body["observed_at"], "observed_at") if body.get("observed_at") else utc_now()))
            row.status, row.synced_at, row.last_error = "SYNCED", utc_now(), None
            synced += 1
        except (ValueError, HTTPException, json.JSONDecodeError) as error:
            row.status, row.last_error = "FAILED", str(getattr(error, "detail", error))[:1000]
            failed += 1
    await session.commit()
    return {"synced": synced, "failed": failed, "remaining": max(0, len(rows) - synced - failed)}


def register_sector_routes(app) -> None:
    app.include_router(router)
