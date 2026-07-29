from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Accession, AllergyRecord, Appointment, AuthAccount, CareTeam, CareTeamMember, ClinicalDocument, ClinicalNote, ClinicalObservation, ClinicalPrivilege,
    ConditionRecord, ConsentRecord, CriticalResultAcknowledgement, DiagnosticReport,
    Encounter, FacilityRegistry, FacilityService, LaboratoryOrder, LaboratoryResult, Notification, NotificationDelivery,
    OrderedTest, OutboxEvent, ProvenanceRecord, QualityControlReview, Referral,
    ResultCorrection, Specimen, SpecimenCollection, SpecimenCustodyEvent, StaffMembership,
    Tenant, TransferRequest,
)
from app.routes import get_db, require_account, require_roles
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import utc_now

router = APIRouter(prefix="/api/v1")
CLINICIAN_ROLES = {"doctor", "specialist"}
LAB_ROLES = {"admin", "laboratory", "lab_scientist", "lab_technician"}


def parse_uuid(value: Any, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"A valid {label} is required") from error


async def verified_membership(session: AsyncSession, account: AuthAccount, facility_id: uuid.UUID | None = None) -> StaffMembership:
    now = utc_now()
    membership = await session.scalar(select(StaffMembership).where(
        StaffMembership.user_id == account.id,
        StaffMembership.hospital_id == (facility_id or account.tenant_id),
        StaffMembership.is_active.is_(True),
        StaffMembership.verification_status == "VERIFIED",
        StaffMembership.employment_status == "ACTIVE",
        StaffMembership.active_from <= now,
        or_(StaffMembership.active_until.is_(None), StaffMembership.active_until >= now),
    ))
    if not membership:
        raise HTTPException(status_code=403, detail="An active verified facility membership is required")
    return membership


async def audit(session: AsyncSession, request: Request, account: AuthAccount, resource_type: str, resource_id: uuid.UUID, action: str, tenant_id: uuid.UUID) -> None:
    session.add(ProvenanceRecord(tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id, action=action, actor_account_id=account.id, source="API"))
    await write_audit_log(session, AuditAction.PATIENT_RECORD_UPDATED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(tenant_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type=resource_type, resource_id=str(resource_id), metadata={"domain_action": action})


def referral_json(row: Referral) -> dict[str, Any]:
    return {"id": str(row.id), "patient_id": str(row.patient_id), "origin_facility_id": str(row.origin_facility_id), "destination_facility_id": str(row.destination_facility_id), "required_capability": row.required_capability, "required_specialty": row.required_specialty, "urgency": row.urgency, "status": row.status, "decision_reason": row.decision_reason, "expires_at": row.expires_at, "created_at": row.created_at}


@router.get("/referrals/options")
async def referral_options(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    await verified_membership(session, account)
    appointments = list((await session.execute(select(Appointment).where(Appointment.doctor_id == account.id, Appointment.hospital_id == account.tenant_id))).scalars().all())
    phones = {appointment.customer_phone for appointment in appointments}
    patients = list((await session.execute(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone.in_(phones)))).scalars().all()) if phones else []
    facilities = list((await session.execute(select(Tenant).where(Tenant.id != account.tenant_id, Tenant.status == "ACTIVE", Tenant.accepts_patients.is_(True)).order_by(Tenant.name))).scalars().all())
    return {"patients": [{"id": str(patient.id), "name": f"{patient.first_name} {patient.last_name}".strip()} for patient in patients], "facilities": [{"id": str(facility.id), "name": facility.name, "location": facility.state_location} for facility in facilities]}

@router.post("/referrals", status_code=201)
async def create_referral(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES | {"hospital_admin"})
    await verified_membership(session, account)
    payload = await request.json()
    patient_id = parse_uuid(payload.get("patient_id"), "patient_id")
    destination_id = parse_uuid(payload.get("destination_facility_id"), "destination_facility_id")
    patient = await session.scalar(select(AuthAccount).where(AuthAccount.id == patient_id, AuthAccount.role == "patient"))
    destination = await session.scalar(select(Tenant).where(Tenant.id == destination_id, Tenant.status == "ACTIVE", Tenant.accepts_patients.is_(True)))
    if not patient or not destination or destination.id == account.tenant_id:
        raise HTTPException(status_code=422, detail="An eligible destination and registered patient are required")
    capability = str(payload.get("required_capability") or "").strip()
    specialty = str(payload.get("required_specialty") or "").strip()
    if not capability or not specialty:
        raise HTTPException(status_code=422, detail="Required capability and specialty are required")
    consent = await session.scalar(select(ConsentRecord).where(ConsentRecord.account_id == patient_id, ConsentRecord.accepted.is_(True)).order_by(ConsentRecord.accepted_at.desc()))
    if not consent:
        raise HTTPException(status_code=409, detail="Patient consent is required before referral data transfer")
    row = Referral(patient_id=patient_id, origin_facility_id=account.tenant_id, destination_facility_id=destination_id, ticket_id=parse_uuid(payload["ticket_id"], "ticket_id") if payload.get("ticket_id") else None, required_capability=capability, required_specialty=specialty, urgency=str(payload.get("urgency") or "ROUTINE").upper(), clinical_summary=str(payload.get("clinical_summary") or "").strip() or None, consent_id=consent.id, expires_at=utc_now() + timedelta(hours=max(1, min(int(payload.get("expires_in_hours") or 24), 168))), created_by_account_id=account.id)
    session.add(row)
    await session.flush()
    await audit(session, request, account, "Referral", row.id, "CREATED", account.tenant_id)
    await session.commit()
    return referral_json(row)


@router.get("/referrals")
async def list_referrals(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    if account.role == "patient":
        query = select(Referral).where(Referral.patient_id == account.id)
    else:
        await verified_membership(session, account)
        query = select(Referral).where(or_(Referral.origin_facility_id == account.tenant_id, Referral.destination_facility_id == account.tenant_id))
    rows = list((await session.execute(query.order_by(Referral.created_at.desc()))).scalars().all())
    return [referral_json(row) for row in rows]


@router.patch("/referrals/{referral_id}/decision")
async def decide_referral(referral_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "department_coordinator"})
    await verified_membership(session, account)
    row = await session.scalar(select(Referral).where(Referral.id == parse_uuid(referral_id, "referral_id"), Referral.destination_facility_id == account.tenant_id).with_for_update())
    if not row:
        raise HTTPException(status_code=404, detail="Referral not found in this destination facility")
    expires_at = row.expires_at.replace(tzinfo=utc_now().tzinfo) if row.expires_at and row.expires_at.tzinfo is None else row.expires_at
    if row.status != "REQUESTED" or (expires_at and expires_at <= utc_now()):
        if row.status == "REQUESTED": row.status = "EXPIRED"
        await session.commit()
        raise HTTPException(status_code=409, detail="Referral is no longer open")
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    reason = str(payload.get("reason") or "").strip()
    if decision not in {"ACCEPTED", "REJECTED"} or (decision == "REJECTED" and len(reason) < 5):
        raise HTTPException(status_code=422, detail="Decision must be ACCEPTED or REJECTED; rejection requires a reason")
    row.status, row.decision_reason, row.decided_by_account_id, row.decided_at = decision, reason or None, account.id, utc_now()
    await audit(session, request, account, "Referral", row.id, decision, account.tenant_id)
    await session.commit()
    return referral_json(row)


@router.post("/referrals/{referral_id}/teleconsultation", status_code=201)
async def grant_teleconsultation(referral_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "department_coordinator"})
    await verified_membership(session, account)
    referral = await session.scalar(select(Referral).where(Referral.id == parse_uuid(referral_id, "referral_id"), Referral.destination_facility_id == account.tenant_id, Referral.status == "ACCEPTED", Referral.consent_withdrawn_at.is_(None)).with_for_update())
    if not referral: raise HTTPException(status_code=404, detail="Accepted consented referral not found")
    payload = await request.json(); specialist_id = parse_uuid(payload.get("specialist_id"), "specialist_id"); hours = max(1, min(int(payload.get("duration_hours") or 8), 72))
    if payload.get("regulatory_approval_confirmed") is not True: raise HTTPException(status_code=422, detail="Country and facility regulatory approval must be confirmed")
    specialist = await session.scalar(select(AuthAccount).where(AuthAccount.id == specialist_id, AuthAccount.role.in_(["doctor", "specialist"]), AuthAccount.is_active.is_(True)))
    source_membership = await session.scalar(select(StaffMembership).where(StaffMembership.user_id == specialist_id, StaffMembership.is_active.is_(True), StaffMembership.verification_status == "VERIFIED", StaffMembership.employment_status == "ACTIVE", StaffMembership.professional_license_number.is_not(None)).order_by(StaffMembership.created_at.desc()))
    if not specialist or not source_membership: raise HTTPException(status_code=422, detail="A verified licensed specialist is required")
    starts_at, ends_at = utc_now(), utc_now() + timedelta(hours=hours)
    membership = StaffMembership(user_id=specialist.id, hospital_id=account.tenant_id, department_id=referral.required_specialty, role="visiting_specialist", specialty_id=referral.required_specialty, professional_license_number=source_membership.professional_license_number, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=starts_at, active_until=ends_at)
    session.add(membership); await session.flush(); session.add(ClinicalPrivilege(membership_id=membership.id, code="TELECONSULTATION", status="ACTIVE", granted_by_account_id=account.id, granted_at=starts_at, expires_at=ends_at))
    encounter = await session.scalar(select(Encounter).where(Encounter.referral_id == referral.id, Encounter.facility_id == account.tenant_id, Encounter.status == "IN_PROGRESS"))
    if not encounter:
        encounter = Encounter(patient_id=referral.patient_id, facility_id=account.tenant_id, referral_id=referral.id, assigned_clinician_id=specialist.id, encounter_type="TELECONSULTATION")
        session.add(encounter); await session.flush()
    team = CareTeam(encounter_id=encounter.id, facility_id=account.tenant_id, name="Temporary teleconsultation team", starts_at=starts_at, ends_at=ends_at)
    session.add(team); await session.flush(); member = CareTeamMember(care_team_id=team.id, user_id=specialist.id, membership_id=membership.id, role="CONSULTING_SPECIALIST", starts_at=starts_at, ends_at=ends_at); session.add(member)
    await audit(session, request, account, "CareTeam", team.id, "TELECONSULTATION_GRANTED", account.tenant_id); await session.commit()
    return {"care_team_id": str(team.id), "membership_id": str(membership.id), "specialist_id": str(specialist.id), "starts_at": starts_at, "expires_at": ends_at}


@router.post("/referrals/{referral_id}/withdraw-consent")
async def withdraw_referral_consent(referral_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"patient"})
    referral = await session.scalar(select(Referral).where(Referral.id == parse_uuid(referral_id, "referral_id"), Referral.patient_id == account.id).with_for_update())
    if not referral: raise HTTPException(status_code=404, detail="Referral not found")
    now = utc_now(); referral.consent_withdrawn_at, referral.status = now, "CONSENT_WITHDRAWN"
    memberships = list((await session.execute(select(StaffMembership).join(CareTeamMember, CareTeamMember.membership_id == StaffMembership.id).join(CareTeam, CareTeam.id == CareTeamMember.care_team_id).join(Encounter, Encounter.id == CareTeam.encounter_id).where(Encounter.referral_id == referral.id, StaffMembership.role == "visiting_specialist", StaffMembership.is_active.is_(True)).with_for_update())).scalars().all())
    for membership in memberships:
        membership.is_active, membership.active_until = False, now
        privilege = await session.scalar(select(ClinicalPrivilege).where(ClinicalPrivilege.membership_id == membership.id, ClinicalPrivilege.status == "ACTIVE").with_for_update())
        if privilege: privilege.status, privilege.revoked_at = "REVOKED", now
    members = list((await session.execute(select(CareTeamMember).join(CareTeam, CareTeam.id == CareTeamMember.care_team_id).join(Encounter, Encounter.id == CareTeam.encounter_id).where(Encounter.referral_id == referral.id, CareTeamMember.status == "ACTIVE").with_for_update())).scalars().all())
    for member in members: member.status, member.ends_at = "REVOKED", now
    await audit(session, request, account, "Referral", referral.id, "CONSENT_WITHDRAWN", referral.origin_facility_id); await session.commit()
    return {"id": str(referral.id), "status": referral.status, "withdrawn_at": now}

@router.post("/referrals/{referral_id}/transfer", status_code=201)
async def create_transfer(referral_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES | {"hospital_admin", "department_coordinator"})
    await verified_membership(session, account)
    row = await session.scalar(select(Referral).where(Referral.id == parse_uuid(referral_id, "referral_id"), Referral.origin_facility_id == account.tenant_id, Referral.status == "ACCEPTED"))
    if not row: raise HTTPException(status_code=404, detail="Accepted origin referral not found")
    if await session.scalar(select(TransferRequest).where(TransferRequest.referral_id == row.id)):
        raise HTTPException(status_code=409, detail="Transfer already exists")
    payload = await request.json()
    transfer = TransferRequest(referral_id=row.id, transport_mode=str(payload.get("transport_mode") or "").strip() or None, handoff_notes=str(payload.get("handoff_notes") or "").strip() or None, status="PLANNED")
    session.add(transfer); await session.flush(); await audit(session, request, account, "TransferRequest", transfer.id, "CREATED", account.tenant_id); await session.commit()
    return {"id": str(transfer.id), "referral_id": str(row.id), "status": transfer.status}


@router.post("/referrals/{referral_id}/encounters", status_code=201)
async def start_referred_encounter(referral_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    await verified_membership(session, account)
    referral = await session.scalar(select(Referral).where(Referral.id == parse_uuid(referral_id, "referral_id"), Referral.destination_facility_id == account.tenant_id, Referral.status == "ACCEPTED"))
    if not referral: raise HTTPException(status_code=404, detail="Accepted destination referral not found")
    encounter = Encounter(patient_id=referral.patient_id, facility_id=account.tenant_id, referral_id=referral.id, assigned_clinician_id=account.id, encounter_type="REFERRED_CARE")
    session.add(encounter); await session.flush(); await audit(session, request, account, "Encounter", encounter.id, "STARTED", account.tenant_id); await session.commit()
    return {"id": str(encounter.id), "patient_id": str(encounter.patient_id), "status": encounter.status, "started_at": encounter.started_at}


@router.post("/appointments/{appointment_id}/encounter", status_code=201)
async def start_appointment_encounter(appointment_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    membership = await verified_membership(session, account)
    appointment = await session.scalar(select(Appointment).where(
        Appointment.id == parse_uuid(appointment_id, "appointment_id"),
        Appointment.hospital_id == membership.hospital_id,
        Appointment.doctor_id == account.id,
        Appointment.status == "BOOKED",
    ))
    if not appointment:
        raise HTTPException(status_code=404, detail="Assigned booked appointment not found")
    existing = await session.scalar(select(Encounter).where(Encounter.appointment_id == appointment.id).order_by(Encounter.started_at.desc()))
    if existing:
        return {"id": str(existing.id), "patient_id": str(existing.patient_id), "status": existing.status, "started_at": existing.started_at}
    patient_id = await session.scalar(select(AuthAccount.id).where(AuthAccount.role == "patient", AuthAccount.phone == appointment.customer_phone))
    encounter = Encounter(
        patient_id=patient_id,
        facility_id=appointment.hospital_id,
        appointment_id=appointment.id,
        assigned_clinician_id=account.id,
        encounter_type="APPOINTMENT",
    )
    if not encounter.patient_id:
        raise HTTPException(status_code=404, detail="Appointment patient account not found")
    session.add(encounter)
    await session.flush()
    await audit(session, request, account, "Encounter", encounter.id, "STARTED", appointment.hospital_id)
    await session.commit()
    return {"id": str(encounter.id), "patient_id": str(encounter.patient_id), "status": encounter.status, "started_at": encounter.started_at}


@router.post("/encounters/{encounter_id}/notes", status_code=201)
async def add_clinical_note(encounter_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    await verified_membership(session, account)
    encounter = await session.scalar(select(Encounter).where(Encounter.id == parse_uuid(encounter_id, "encounter_id"), Encounter.facility_id == account.tenant_id, Encounter.assigned_clinician_id == account.id))
    if not encounter: raise HTTPException(status_code=404, detail="Assigned encounter not found")
    payload = await request.json(); body = str(payload.get("body") or "").strip()
    if len(body) < 3: raise HTTPException(status_code=422, detail="Clinical note is required")
    note = ClinicalNote(encounter_id=encounter.id, patient_id=encounter.patient_id, facility_id=encounter.facility_id, author_id=account.id, note_type=str(payload.get("note_type") or "PROGRESS").upper(), body=body)
    session.add(note); await session.flush(); await audit(session, request, account, "ClinicalNote", note.id, "CREATED", account.tenant_id); await session.commit()
    return {"id": str(note.id), "encounter_id": str(encounter.id), "status": note.status, "created_at": note.created_at}


def order_json(order: LaboratoryOrder, tests: list[OrderedTest] | None = None) -> dict[str, Any]:
    return {"id": str(order.id), "patient_id": str(order.patient_id), "ordering_facility_id": str(order.ordering_facility_id), "laboratory_id": str(order.laboratory_id), "ordering_clinician_id": str(order.ordering_clinician_id), "priority": order.priority, "status": order.status, "created_at": order.created_at, "tests": [{"id": str(test.id), "test_code": test.test_code, "display": test.display, "loinc_code": test.loinc_code, "status": test.status} for test in (tests or [])]}


@router.post("/laboratory/orders", status_code=201)
async def create_lab_order(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    membership = await verified_membership(session, account)
    payload = await request.json(); patient_id = parse_uuid(payload.get("patient_id"), "patient_id"); laboratory_id = parse_uuid(payload.get("laboratory_id"), "laboratory_id")
    patient = await session.scalar(select(AuthAccount).where(AuthAccount.id == patient_id, AuthAccount.role == "patient")); laboratory = await session.scalar(select(Tenant).where(Tenant.id == laboratory_id, Tenant.status == "ACTIVE"))
    tests = payload.get("tests")
    if not patient or not laboratory or not isinstance(tests, list) or not tests: raise HTTPException(status_code=422, detail="Registered patient, active laboratory, and at least one test are required")
    order = LaboratoryOrder(patient_id=patient.id, ordering_facility_id=membership.hospital_id, laboratory_id=laboratory.id, encounter_id=parse_uuid(payload["encounter_id"], "encounter_id") if payload.get("encounter_id") else None, ordering_clinician_id=account.id, clinical_context=str(payload.get("clinical_context") or "").strip() or None, priority=str(payload.get("priority") or "ROUTINE").upper(), patient_release_policy=str(payload.get("patient_release_policy") or "AFTER_FINAL").upper())
    session.add(order); await session.flush()
    rows = [OrderedTest(order_id=order.id, test_code=str(item.get("test_code") or "").strip(), display=str(item.get("display") or "").strip(), loinc_code=str(item.get("loinc_code") or "").strip() or None, specimen_type=str(item.get("specimen_type") or "").strip() or None) for item in tests if isinstance(item, dict) and item.get("test_code") and item.get("display")]
    if not rows: raise HTTPException(status_code=422, detail="Every ordered test requires a code and display name")
    session.add_all(rows); await audit(session, request, account, "LaboratoryOrder", order.id, "ORDERED", order.ordering_facility_id); await session.commit()
    return order_json(order, rows)


async def require_lab_access(request: Request, session: AsyncSession, order_id: uuid.UUID | None = None) -> tuple[AuthAccount, LaboratoryOrder | None]:
    account = await require_roles(request, session, LAB_ROLES)
    order = await session.scalar(select(LaboratoryOrder).where(LaboratoryOrder.id == order_id, LaboratoryOrder.laboratory_id == account.tenant_id)) if order_id else None
    if order_id and not order: raise HTTPException(status_code=404, detail="Laboratory order not found in this workspace")
    return account, order


@router.get("/lab/dashboard")
async def lab_dashboard(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    order_counts = dict((await session.execute(select(LaboratoryOrder.status, func.count(LaboratoryOrder.id)).where(LaboratoryOrder.laboratory_id == account.tenant_id).group_by(LaboratoryOrder.status))).all())
    critical_count = await session.scalar(select(func.count(LaboratoryResult.id)).join(OrderedTest, OrderedTest.id == LaboratoryResult.ordered_test_id).join(LaboratoryOrder, LaboratoryOrder.id == OrderedTest.order_id).outerjoin(CriticalResultAcknowledgement, CriticalResultAcknowledgement.result_id == LaboratoryResult.id).where(LaboratoryOrder.laboratory_id == account.tenant_id, LaboratoryResult.is_critical.is_(True), CriticalResultAcknowledgement.id.is_(None)))
    return {"stats": [{"title": "New requests", "value": order_counts.get("REQUESTED", 0), "tone": "sky"}, {"title": "In progress", "value": sum(count for status, count in order_counts.items() if status in {"ACCEPTED", "SPECIMEN_COLLECTED", "RESULTS_PENDING_REVIEW"}), "tone": "amber"}, {"title": "Critical results", "value": critical_count or 0, "tone": "rose"}, {"title": "Completed reports", "value": order_counts.get("RELEASED", 0), "tone": "slate"}], "activity": []}


@router.get("/lab/specimens")
async def lab_specimens(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return await lab_collections(request, session)


@router.get("/lab/worklist")
async def lab_worklist(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    rows = list((await session.execute(select(OrderedTest, LaboratoryOrder).join(LaboratoryOrder, LaboratoryOrder.id == OrderedTest.order_id).where(LaboratoryOrder.laboratory_id == account.tenant_id, OrderedTest.status != "FINAL").order_by(LaboratoryOrder.created_at))).all())
    return {"items": [{"id": str(test.id), "title": test.display, "description": test.loinc_code or test.test_code, "status": test.status, "created_at": order.created_at} for test, order in rows]}


@router.get("/lab/critical-results")
async def lab_critical_results(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    rows = list((await session.execute(select(LaboratoryResult, OrderedTest, CriticalResultAcknowledgement).join(OrderedTest, OrderedTest.id == LaboratoryResult.ordered_test_id).join(LaboratoryOrder, LaboratoryOrder.id == OrderedTest.order_id).outerjoin(CriticalResultAcknowledgement, CriticalResultAcknowledgement.result_id == LaboratoryResult.id).where(LaboratoryOrder.laboratory_id == account.tenant_id, LaboratoryResult.is_critical.is_(True)).order_by(LaboratoryResult.observed_at.desc()))).all())
    return {"items": [{"id": str(result.id), "title": test.display, "description": "Acknowledged" if acknowledgement else "Clinician acknowledgement required", "status": "ACKNOWLEDGED" if acknowledgement else "CRITICAL", "created_at": result.observed_at} for result, test, acknowledgement in rows]}


@router.get("/lab/equipment")
async def lab_equipment(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    registry = await session.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == account.tenant_id))
    services = list((await session.execute(select(FacilityService).where(FacilityService.facility_registry_id == registry.id).order_by(FacilityService.service_code))).scalars().all()) if registry else []
    return {"items": [{"id": str(service.id), "title": service.service_code.replace("_", " ").title(), "description": service.specialty_code, "status": service.status} for service in services]}

@router.get("/lab/requests")
async def lab_requests(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    orders = list((await session.execute(select(LaboratoryOrder).where(LaboratoryOrder.laboratory_id == account.tenant_id).order_by(LaboratoryOrder.created_at.desc()))).scalars().all())
    items = []
    for row in orders:
        tests = list((await session.execute(select(OrderedTest).where(OrderedTest.order_id == row.id).order_by(OrderedTest.display))).scalars().all())
        items.append({"id": str(row.id), "title": f"Laboratory order {str(row.id)[:8]}", "description": row.priority.title(), "status": row.status, "created_at": row.created_at, "tests": [{"id": str(test.id), "display": test.display, "test_code": test.test_code, "loinc_code": test.loinc_code, "status": test.status} for test in tests]})
    return {"items": items}


@router.get("/lab/collections")
async def lab_collections(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    rows = list((await session.execute(select(Specimen, LaboratoryOrder).join(LaboratoryOrder, LaboratoryOrder.id == Specimen.order_id).where(LaboratoryOrder.laboratory_id == account.tenant_id).order_by(Specimen.collected_at.desc()))).all())
    return {"items": [{"id": str(specimen.id), "title": specimen.accession_number, "description": specimen.specimen_type, "status": specimen.status, "created_at": specimen.collected_at or order.created_at} for specimen, order in rows]}


@router.post("/laboratory/orders/{order_id}/accept")
async def accept_lab_order(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, order = await require_lab_access(request, session, parse_uuid(order_id, "order_id")); assert order
    if order.status != "REQUESTED": raise HTTPException(status_code=409, detail="Order is not awaiting acceptance")
    order.status = "ACCEPTED"; await audit(session, request, account, "LaboratoryOrder", order.id, "ACCEPTED", account.tenant_id); await session.commit(); return order_json(order)


@router.post("/laboratory/orders/{order_id}/specimens", status_code=201)
async def collect_specimen(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, order = await require_lab_access(request, session, parse_uuid(order_id, "order_id")); assert order
    if order.status not in {"ACCEPTED", "COLLECTION_SCHEDULED", "RECOLLECTION_REQUIRED"}: raise HTTPException(status_code=409, detail="Order is not ready for collection")
    payload = await request.json(); specimen_type = str(payload.get("specimen_type") or "").strip()
    if not specimen_type: raise HTTPException(status_code=422, detail="Specimen type is required")
    collected_at = utc_now(); specimen = Specimen(order_id=order.id, accession_number=f"ACC-{utc_now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}", specimen_type=specimen_type, status="COLLECTED", collected_at=collected_at, collector_id=account.id)
    session.add(specimen); await session.flush(); session.add(Accession(specimen_id=specimen.id, accession_number=specimen.accession_number, laboratory_id=account.tenant_id, created_by_id=account.id)); session.add_all([SpecimenCollection(specimen_id=specimen.id, collector_id=account.id, collection_site=str(payload.get("collection_site") or "").strip() or None, collected_at=collected_at, notes=str(payload.get("notes") or "").strip() or None), SpecimenCustodyEvent(specimen_id=specimen.id, actor_id=account.id, event_type="COLLECTED", location=str(payload.get("collection_site") or "").strip() or None)])
    order.status = "SPECIMEN_COLLECTED"; await audit(session, request, account, "Specimen", specimen.id, "COLLECTED", account.tenant_id); await session.commit(); return {"id": str(specimen.id), "accession_number": specimen.accession_number, "status": specimen.status}


@router.patch("/laboratory/specimens/{specimen_id}/status")
async def update_specimen(specimen_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, LAB_ROLES); payload = await request.json(); status = str(payload.get("status") or "").upper(); reason = str(payload.get("reason") or "").strip()
    specimen = await session.scalar(select(Specimen).join(LaboratoryOrder, LaboratoryOrder.id == Specimen.order_id).where(Specimen.id == parse_uuid(specimen_id, "specimen_id"), LaboratoryOrder.laboratory_id == account.tenant_id).with_for_update())
    if not specimen: raise HTTPException(status_code=404, detail="Specimen not found")
    if status not in {"RECEIVED", "REJECTED", "RECOLLECTION_REQUIRED", "PROCESSING"} or (status in {"REJECTED", "RECOLLECTION_REQUIRED"} and len(reason) < 5): raise HTTPException(status_code=422, detail="Valid status and rejection reason are required")
    specimen.status, specimen.rejection_reason = status, reason or None
    if status == "RECEIVED": specimen.received_at = utc_now()
    session.add(SpecimenCustodyEvent(specimen_id=specimen.id, actor_id=account.id, event_type=status, location=str(payload.get("location") or "").strip() or None)); await audit(session, request, account, "Specimen", specimen.id, status, account.tenant_id); await session.commit(); return {"id": str(specimen.id), "status": specimen.status}


@router.post("/laboratory/orders/{order_id}/results", status_code=201)
async def enter_result(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, order = await require_lab_access(request, session, parse_uuid(order_id, "order_id")); assert order
    payload = await request.json(); test_id = parse_uuid(payload.get("ordered_test_id"), "ordered_test_id"); test = await session.scalar(select(OrderedTest).where(OrderedTest.id == test_id, OrderedTest.order_id == order.id))
    if not test: raise HTTPException(status_code=404, detail="Ordered test not found")
    value = str(payload.get("value") or "").strip()
    if not value: raise HTTPException(status_code=422, detail="Result value is required")
    result = LaboratoryResult(ordered_test_id=test.id, patient_id=order.patient_id, value=value, unit=str(payload.get("unit") or "").strip() or None, reference_range=str(payload.get("reference_range") or "").strip() or None, interpretation=str(payload.get("interpretation") or "").strip() or None, is_critical=bool(payload.get("is_critical")), status=str(payload.get("status") or "PRELIMINARY").upper(), entered_by_id=account.id)
    session.add(result); test.status = "RESULTED"; order.status = "RESULTS_PENDING_REVIEW"; await session.flush()
    if result.is_critical:
        notification = Notification(tenant_id=order.ordering_facility_id, recipient_user_id=order.ordering_clinician_id, recipient_account_id=order.ordering_clinician_id, recipient_role="doctor", hospital_id=order.ordering_facility_id, event_type="CRITICAL_LAB_RESULT", title="Critical laboratory result", body="A critical laboratory result requires immediate review and acknowledgement.", priority="CRITICAL")
        session.add(notification); await session.flush(); session.add_all([NotificationDelivery(notification_id=notification.id, channel="REALTIME", status="PENDING"), OutboxEvent(tenant_id=order.ordering_facility_id, aggregate_type="Notification", aggregate_id=notification.id, event_type="CRITICAL_LAB_RESULT", recipient_user_id=order.ordering_clinician_id, payload_json=json.dumps({"notification_id": str(notification.id), "laboratory_result_id": str(result.id), "recipient_user_id": str(order.ordering_clinician_id)}), classification="RESTRICTED")])
    await audit(session, request, account, "LaboratoryResult", result.id, "ENTERED", account.tenant_id); await session.commit(); return {"id": str(result.id), "status": result.status, "is_critical": result.is_critical}


@router.post("/laboratory/results/{result_id}/correct")
async def correct_result(result_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, LAB_ROLES)
    result = await session.scalar(select(LaboratoryResult).join(OrderedTest, OrderedTest.id == LaboratoryResult.ordered_test_id).join(LaboratoryOrder, LaboratoryOrder.id == OrderedTest.order_id).where(LaboratoryResult.id == parse_uuid(result_id, "result_id"), LaboratoryOrder.laboratory_id == account.tenant_id).with_for_update())
    if not result: raise HTTPException(status_code=404, detail="Laboratory result not found")
    payload = await request.json(); corrected_value = str(payload.get("corrected_value") or "").strip(); reason = str(payload.get("reason") or "").strip()
    if not corrected_value or len(reason) < 5: raise HTTPException(status_code=422, detail="Corrected value and correction reason are required")
    correction = ResultCorrection(result_id=result.id, previous_value=result.value, corrected_value=corrected_value, reason=reason, corrected_by_id=account.id)
    session.add(correction); result.value, result.status = corrected_value, "CORRECTED"; await session.flush(); await audit(session, request, account, "LaboratoryResult", result.id, "CORRECTED", account.tenant_id); await session.commit()
    return {"id": str(result.id), "status": result.status, "correction_id": str(correction.id)}

@router.post("/laboratory/orders/{order_id}/finalize")
async def finalize_report(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, order = await require_lab_access(request, session, parse_uuid(order_id, "order_id")); assert order
    payload = await request.json(); decision = str(payload.get("decision") or "APPROVED").upper()
    if decision not in {"APPROVED", "REJECTED"}: raise HTTPException(status_code=422, detail="Quality decision must be APPROVED or REJECTED")
    report = await session.scalar(select(DiagnosticReport).where(DiagnosticReport.order_id == order.id).with_for_update())
    if not report: report = DiagnosticReport(order_id=order.id, conclusion=str(payload.get("conclusion") or "").strip() or None, pdf_storage_key=str(payload.get("pdf_storage_key") or "").strip() or None); session.add(report); await session.flush()
    session.add(QualityControlReview(report_id=report.id, reviewer_id=account.id, decision=decision, notes=str(payload.get("notes") or "").strip() or None))
    if decision == "APPROVED": report.status, report.reviewed_by_id, report.finalized_at, order.status = "FINAL", account.id, utc_now(), "FINAL"
    await audit(session, request, account, "DiagnosticReport", report.id, decision, account.tenant_id); await session.commit(); return {"id": str(report.id), "order_id": str(order.id), "status": report.status}


@router.post("/laboratory/results/{result_id}/acknowledge")
async def acknowledge_critical_result(result_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    result = await session.scalar(select(LaboratoryResult).where(LaboratoryResult.id == parse_uuid(result_id, "result_id"), LaboratoryResult.is_critical.is_(True)))
    if not result: raise HTTPException(status_code=404, detail="Critical result not found")
    test = await session.get(OrderedTest, result.ordered_test_id); order = await session.get(LaboratoryOrder, test.order_id) if test else None
    if not order or order.ordering_clinician_id != account.id: raise HTTPException(status_code=404, detail="Critical result not found")
    existing = await session.scalar(select(CriticalResultAcknowledgement).where(CriticalResultAcknowledgement.result_id == result.id))
    if existing: return {"id": str(existing.id), "acknowledged_at": existing.acknowledged_at}
    payload = await request.json(); row = CriticalResultAcknowledgement(result_id=result.id, clinician_id=account.id, action_taken=str(payload.get("action_taken") or "").strip() or None); session.add(row); await session.flush(); await audit(session, request, account, "LaboratoryResult", result.id, "ACKNOWLEDGED", order.ordering_facility_id); await session.commit(); return {"id": str(row.id), "acknowledged_at": row.acknowledged_at}


@router.post("/laboratory/orders/{order_id}/release")
async def release_report(order_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, order = await require_lab_access(request, session, parse_uuid(order_id, "order_id")); assert order
    report = await session.scalar(select(DiagnosticReport).where(DiagnosticReport.order_id == order.id).with_for_update())
    if not report or report.status != "FINAL": raise HTTPException(status_code=409, detail="Only a final quality-reviewed report can be released")
    critical = await session.scalar(select(LaboratoryResult).join(OrderedTest, OrderedTest.id == LaboratoryResult.ordered_test_id).where(OrderedTest.order_id == order.id, LaboratoryResult.is_critical.is_(True)))
    if critical and not await session.scalar(select(CriticalResultAcknowledgement).where(CriticalResultAcknowledgement.result_id == critical.id)):
        raise HTTPException(status_code=409, detail="Critical result must be acknowledged before patient release")
    report.released_to_patient_at = utc_now(); order.status = "RELEASED"
    notification = Notification(tenant_id=order.ordering_facility_id, recipient_user_id=order.patient_id, recipient_account_id=order.patient_id, recipient_role="patient", hospital_id=order.ordering_facility_id, event_type="LAB_RESULT", title="Laboratory results available", body="Your finalized laboratory report is available in your health history.")
    session.add(notification); await audit(session, request, account, "DiagnosticReport", report.id, "RELEASED", account.tenant_id); await session.commit(); return {"id": str(report.id), "status": order.status, "released_at": report.released_to_patient_at}


@router.get("/lab/results")
async def lab_results(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, _ = await require_lab_access(request, session)
    rows = list((await session.execute(select(DiagnosticReport, LaboratoryOrder).join(LaboratoryOrder, LaboratoryOrder.id == DiagnosticReport.order_id).where(LaboratoryOrder.laboratory_id == account.tenant_id).order_by(LaboratoryOrder.created_at.desc()))).all())
    return {"items": [{"id": str(report.id), "title": f"Diagnostic report {str(report.id)[:8]}", "description": report.conclusion, "status": report.status, "created_at": order.created_at} for report, order in rows]}


@router.get("/patients/me/laboratory-results")
async def patient_lab_results(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_roles(request, session, {"patient"})
    rows = list((await session.execute(select(DiagnosticReport, LaboratoryOrder).join(LaboratoryOrder, LaboratoryOrder.id == DiagnosticReport.order_id).where(LaboratoryOrder.patient_id == account.id, DiagnosticReport.released_to_patient_at.is_not(None)).order_by(DiagnosticReport.released_to_patient_at.desc()))).all())
    return [{"id": str(report.id), "status": report.status, "conclusion": report.conclusion, "released_at": report.released_to_patient_at} for report, _order in rows]


def register_clinical_routes(app: Any) -> None:
    app.include_router(router)
