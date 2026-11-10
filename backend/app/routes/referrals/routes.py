from __future__ import annotations

from fastapi import APIRouter

from app.routes.clinical_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/referrals/options")
async def referral_options(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    await verified_membership(session, account)
    appointments = list(
        (
            await session.execute(
                select(Appointment).where(
                    Appointment.doctor_id == account.id,
                    Appointment.hospital_id == account.tenant_id,
                )
            )
        )
        .scalars()
        .all()
    )
    phones = {appointment.customer_phone for appointment in appointments}
    patients = (
        list(
            (
                await session.execute(
                    select(AuthAccount).where(
                        AuthAccount.role == "patient", AuthAccount.phone.in_(phones)
                    )
                )
            )
            .scalars()
            .all()
        )
        if phones
        else []
    )
    facilities = list(
        (
            await session.execute(
                select(Tenant)
                .where(
                    Tenant.id != account.tenant_id,
                    Tenant.status == "ACTIVE",
                    Tenant.accepts_patients.is_(True),
                )
                .order_by(Tenant.name)
            )
        )
        .scalars()
        .all()
    )
    return {
        "patients": [
            {
                "id": str(patient.id),
                "name": f"{patient.first_name} {patient.last_name}".strip(),
            }
            for patient in patients
        ],
        "facilities": [
            {
                "id": str(facility.id),
                "name": facility.name,
                "location": facility.state_location,
            }
            for facility in facilities
        ],
    }


@router.post("/referrals", status_code=201)
async def create_referral(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(
        request, session, CLINICIAN_ROLES | {"hospital_admin"}
    )
    await verified_membership(session, account)
    payload = await request.json()
    patient_id = parse_uuid(payload.get("patient_id"), "patient_id")
    destination_id = parse_uuid(
        payload.get("destination_facility_id"), "destination_facility_id"
    )
    patient = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.id == patient_id, AuthAccount.role == "patient"
        )
    )
    destination = await session.scalar(
        select(Tenant).where(
            Tenant.id == destination_id,
            Tenant.status == "ACTIVE",
            Tenant.accepts_patients.is_(True),
        )
    )
    if not patient or not destination or destination.id == account.tenant_id:
        raise HTTPException(
            status_code=422,
            detail="An eligible destination and registered patient are required",
        )
    capability = str(payload.get("required_capability") or "").strip()
    specialty = str(payload.get("required_specialty") or "").strip()
    if not capability or not specialty:
        raise HTTPException(
            status_code=422, detail="Required capability and specialty are required"
        )
    consent = await session.scalar(
        select(ConsentRecord)
        .where(ConsentRecord.account_id == patient_id, ConsentRecord.accepted.is_(True))
        .order_by(ConsentRecord.accepted_at.desc())
    )
    if not consent:
        raise HTTPException(
            status_code=409,
            detail="Patient consent is required before referral data transfer",
        )
    row = Referral(
        patient_id=patient_id,
        origin_facility_id=account.tenant_id,
        destination_facility_id=destination_id,
        ticket_id=(
            parse_uuid(payload["ticket_id"], "ticket_id")
            if payload.get("ticket_id")
            else None
        ),
        required_capability=capability,
        required_specialty=specialty,
        urgency=str(payload.get("urgency") or "ROUTINE").upper(),
        clinical_summary=str(payload.get("clinical_summary") or "").strip() or None,
        consent_id=consent.id,
        expires_at=utc_now()
        + timedelta(hours=max(1, min(int(payload.get("expires_in_hours") or 24), 168))),
        created_by_account_id=account.id,
    )
    session.add(row)
    await session.flush()
    await audit(
        session, request, account, "Referral", row.id, "CREATED", account.tenant_id
    )
    await session.commit()
    return referral_json(row)


@router.get("/referrals")
async def list_referrals(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    if account.role == "patient":
        query = select(Referral).where(Referral.patient_id == account.id)
    else:
        await verified_membership(session, account)
        query = select(Referral).where(
            or_(
                Referral.origin_facility_id == account.tenant_id,
                Referral.destination_facility_id == account.tenant_id,
            )
        )
    rows = list(
        (await session.execute(query.order_by(Referral.created_at.desc())))
        .scalars()
        .all()
    )
    return [referral_json(row) for row in rows]


@router.patch("/referrals/{referral_id}/decision")
async def decide_referral(
    referral_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(
        request, session, {"hospital_admin", "department_coordinator"}
    )
    await verified_membership(session, account)
    row = await session.scalar(
        select(Referral)
        .where(
            Referral.id == parse_uuid(referral_id, "referral_id"),
            Referral.destination_facility_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not row:
        raise HTTPException(
            status_code=404, detail="Referral not found in this destination facility"
        )
    expires_at = (
        row.expires_at.replace(tzinfo=utc_now().tzinfo)
        if row.expires_at and row.expires_at.tzinfo is None
        else row.expires_at
    )
    if row.status != "REQUESTED" or (expires_at and expires_at <= utc_now()):
        if row.status == "REQUESTED":
            row.status = "EXPIRED"
        await session.commit()
        raise HTTPException(status_code=409, detail="Referral is no longer open")
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    reason = str(payload.get("reason") or "").strip()
    if decision not in {"ACCEPTED", "REJECTED"} or (
        decision == "REJECTED" and len(reason) < 5
    ):
        raise HTTPException(
            status_code=422,
            detail="Decision must be ACCEPTED or REJECTED; rejection requires a reason",
        )
    row.status, row.decision_reason, row.decided_by_account_id, row.decided_at = (
        decision,
        reason or None,
        account.id,
        utc_now(),
    )
    await audit(
        session, request, account, "Referral", row.id, decision, account.tenant_id
    )
    await session.commit()
    return referral_json(row)


@router.post("/referrals/{referral_id}/teleconsultation", status_code=201)
async def grant_teleconsultation(
    referral_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(
        request, session, {"hospital_admin", "department_coordinator"}
    )
    await verified_membership(session, account)
    referral = await session.scalar(
        select(Referral)
        .where(
            Referral.id == parse_uuid(referral_id, "referral_id"),
            Referral.destination_facility_id == account.tenant_id,
            Referral.status == "ACCEPTED",
            Referral.consent_withdrawn_at.is_(None),
        )
        .with_for_update()
    )
    if not referral:
        raise HTTPException(
            status_code=404, detail="Accepted consented referral not found"
        )
    payload = await request.json()
    specialist_id = parse_uuid(payload.get("specialist_id"), "specialist_id")
    hours = max(1, min(int(payload.get("duration_hours") or 8), 72))
    if payload.get("regulatory_approval_confirmed") is not True:
        raise HTTPException(
            status_code=422,
            detail="Country and facility regulatory approval must be confirmed",
        )
    specialist = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.id == specialist_id,
            AuthAccount.role.in_(["doctor", "specialist"]),
            AuthAccount.is_active.is_(True),
        )
    )
    source_membership = await session.scalar(
        select(StaffMembership)
        .where(
            StaffMembership.user_id == specialist_id,
            StaffMembership.is_active.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
            StaffMembership.professional_license_number.is_not(None),
        )
        .order_by(StaffMembership.created_at.desc())
    )
    if not specialist or not source_membership:
        raise HTTPException(
            status_code=422, detail="A verified licensed specialist is required"
        )
    starts_at, ends_at = utc_now(), utc_now() + timedelta(hours=hours)
    membership = StaffMembership(
        user_id=specialist.id,
        hospital_id=account.tenant_id,
        department_id=referral.required_specialty,
        role="visiting_specialist",
        specialty_id=referral.required_specialty,
        professional_license_number=source_membership.professional_license_number,
        verification_status="VERIFIED",
        employment_status="ACTIVE",
        is_active=True,
        is_on_duty=True,
        active_from=starts_at,
        active_until=ends_at,
    )
    session.add(membership)
    await session.flush()
    session.add(
        ClinicalPrivilege(
            membership_id=membership.id,
            code="TELECONSULTATION",
            status="ACTIVE",
            granted_by_account_id=account.id,
            granted_at=starts_at,
            expires_at=ends_at,
        )
    )
    encounter = await session.scalar(
        select(Encounter).where(
            Encounter.referral_id == referral.id,
            Encounter.facility_id == account.tenant_id,
            Encounter.status == "IN_PROGRESS",
        )
    )
    if not encounter:
        encounter = Encounter(
            patient_id=referral.patient_id,
            facility_id=account.tenant_id,
            referral_id=referral.id,
            assigned_clinician_id=specialist.id,
            encounter_type="TELECONSULTATION",
        )
        session.add(encounter)
        await session.flush()
    team = CareTeam(
        encounter_id=encounter.id,
        facility_id=account.tenant_id,
        name="Temporary teleconsultation team",
        starts_at=starts_at,
        ends_at=ends_at,
    )
    session.add(team)
    await session.flush()
    member = CareTeamMember(
        care_team_id=team.id,
        user_id=specialist.id,
        membership_id=membership.id,
        role="CONSULTING_SPECIALIST",
        starts_at=starts_at,
        ends_at=ends_at,
    )
    session.add(member)
    await audit(
        session,
        request,
        account,
        "CareTeam",
        team.id,
        "TELECONSULTATION_GRANTED",
        account.tenant_id,
    )
    await session.commit()
    return {
        "care_team_id": str(team.id),
        "membership_id": str(membership.id),
        "specialist_id": str(specialist.id),
        "starts_at": starts_at,
        "expires_at": ends_at,
    }


@router.post("/referrals/{referral_id}/withdraw-consent")
async def withdraw_referral_consent(
    referral_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"patient"})
    referral = await session.scalar(
        select(Referral)
        .where(
            Referral.id == parse_uuid(referral_id, "referral_id"),
            Referral.patient_id == account.id,
        )
        .with_for_update()
    )
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    now = utc_now()
    referral.consent_withdrawn_at, referral.status = now, "CONSENT_WITHDRAWN"
    memberships = list(
        (
            await session.execute(
                select(StaffMembership)
                .join(
                    CareTeamMember, CareTeamMember.membership_id == StaffMembership.id
                )
                .join(CareTeam, CareTeam.id == CareTeamMember.care_team_id)
                .join(Encounter, Encounter.id == CareTeam.encounter_id)
                .where(
                    Encounter.referral_id == referral.id,
                    StaffMembership.role == "visiting_specialist",
                    StaffMembership.is_active.is_(True),
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for membership in memberships:
        membership.is_active, membership.active_until = False, now
        privilege = await session.scalar(
            select(ClinicalPrivilege)
            .where(
                ClinicalPrivilege.membership_id == membership.id,
                ClinicalPrivilege.status == "ACTIVE",
            )
            .with_for_update()
        )
        if privilege:
            privilege.status, privilege.revoked_at = "REVOKED", now
    members = list(
        (
            await session.execute(
                select(CareTeamMember)
                .join(CareTeam, CareTeam.id == CareTeamMember.care_team_id)
                .join(Encounter, Encounter.id == CareTeam.encounter_id)
                .where(
                    Encounter.referral_id == referral.id,
                    CareTeamMember.status == "ACTIVE",
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for member in members:
        member.status, member.ends_at = "REVOKED", now
    await audit(
        session,
        request,
        account,
        "Referral",
        referral.id,
        "CONSENT_WITHDRAWN",
        referral.origin_facility_id,
    )
    await session.commit()
    return {"id": str(referral.id), "status": referral.status, "withdrawn_at": now}


@router.post("/referrals/{referral_id}/transfer", status_code=201)
async def create_transfer(
    referral_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(
        request, session, CLINICIAN_ROLES | {"hospital_admin", "department_coordinator"}
    )
    await verified_membership(session, account)
    row = await session.scalar(
        select(Referral).where(
            Referral.id == parse_uuid(referral_id, "referral_id"),
            Referral.origin_facility_id == account.tenant_id,
            Referral.status == "ACCEPTED",
        )
    )
    if not row:
        raise HTTPException(
            status_code=404, detail="Accepted origin referral not found"
        )
    if await session.scalar(
        select(TransferRequest).where(TransferRequest.referral_id == row.id)
    ):
        raise HTTPException(status_code=409, detail="Transfer already exists")
    payload = await request.json()
    transfer = TransferRequest(
        referral_id=row.id,
        transport_mode=str(payload.get("transport_mode") or "").strip() or None,
        handoff_notes=str(payload.get("handoff_notes") or "").strip() or None,
        status="PLANNED",
    )
    session.add(transfer)
    await session.flush()
    await audit(
        session,
        request,
        account,
        "TransferRequest",
        transfer.id,
        "CREATED",
        account.tenant_id,
    )
    await session.commit()
    return {
        "id": str(transfer.id),
        "referral_id": str(row.id),
        "status": transfer.status,
    }


@router.post("/referrals/{referral_id}/encounters", status_code=201)
async def start_referred_encounter(
    referral_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    await verified_membership(session, account)
    referral = await session.scalar(
        select(Referral).where(
            Referral.id == parse_uuid(referral_id, "referral_id"),
            Referral.destination_facility_id == account.tenant_id,
            Referral.status == "ACCEPTED",
        )
    )
    if not referral:
        raise HTTPException(
            status_code=404, detail="Accepted destination referral not found"
        )
    encounter = Encounter(
        patient_id=referral.patient_id,
        facility_id=account.tenant_id,
        referral_id=referral.id,
        assigned_clinician_id=account.id,
        encounter_type="REFERRED_CARE",
    )
    session.add(encounter)
    await session.flush()
    await audit(
        session,
        request,
        account,
        "Encounter",
        encounter.id,
        "STARTED",
        account.tenant_id,
    )
    await session.commit()
    return {
        "id": str(encounter.id),
        "patient_id": str(encounter.patient_id),
        "status": encounter.status,
        "started_at": encounter.started_at,
    }
