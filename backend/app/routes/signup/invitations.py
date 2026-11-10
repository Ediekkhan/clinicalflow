from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/hospital/staff-invitations", status_code=201)
async def create_staff_invitation(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, workspace, _tenant = await require_hospital_membership(
        request, session, roles={"hospital_admin", "department_coordinator"}
    )
    payload = await request.json()
    department_id = str(payload.get("department_id") or "").strip()
    intended_role = str(payload.get("role") or "").strip().lower()
    if intended_role not in {"doctor", "specialist", "nurse"}:
        raise HTTPException(
            status_code=422, detail="Role must be doctor, specialist, or nurse"
        )
    if (
        intended_role in {"doctor", "specialist"}
        and not str(payload.get("specialty_id") or "").strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="A specialty is required for doctors and specialists",
        )
    if (
        workspace.role == "department_coordinator"
        and department_id != workspace.department_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Coordinators may invite staff only to their own department",
        )
    department = await resolve_hospital_department(
        session, workspace.hospital_id, department_id
    )
    if department:
        department_id = department.name
    if not department:
        raise HTTPException(
            status_code=422, detail="Select an active hospital department"
        )
    email = str(payload.get("email") or "").strip().lower() or None
    phone = str(payload.get("phone") or "").strip() or None
    if not email and not phone:
        raise HTTPException(
            status_code=422, detail="An invited email or phone number is required"
        )
    raw_token = secrets.token_urlsafe(32)
    expires_in_days = max(1, min(int(payload.get("expires_in_days") or 7), 30))
    invitation = StaffInvitation(
        hospital_id=workspace.hospital_id,
        organization_id=workspace.hospital_id,
        department_id=department_id,
        permitted_role=intended_role,
        intended_role=intended_role,
        specialty_id=str(payload.get("specialty_id") or "").strip() or None,
        employment_type=str(payload.get("employment_type") or "").strip() or None,
        invitation_code=f"staff-{secrets.token_hex(8)}",
        token_hash=token_hash(raw_token),
        invited_email=email,
        invited_phone=phone,
        expires_at=utc_now() + timedelta(days=expires_in_days),
        created_by_account_id=account.id,
        invited_by=account.id,
    )
    session.add(invitation)
    await session.commit()
    return {
        "id": str(invitation.id),
        "invite_token": raw_token,
        "signup_path": f"/signup/{'nurse' if intended_role == 'nurse' else 'specialist'}?invite={raw_token}",
        "expires_at": invitation.expires_at,
    }


@router.get("/hospital/staff-membership-requests")
async def list_staff_membership_requests(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, workspace, _tenant = await require_hospital_membership(
        request, session, roles={"hospital_admin", "department_coordinator"}
    )
    query = (
        select(StaffMembership, AuthAccount)
        .join(AuthAccount, AuthAccount.id == StaffMembership.user_id)
        .where(
            StaffMembership.hospital_id == workspace.hospital_id,
            StaffMembership.verification_status == "PENDING_HOSPITAL_APPROVAL",
        )
    )
    if workspace.role == "department_coordinator":
        query = query.where(StaffMembership.department_id == workspace.department_id)
    rows = (await session.execute(query.order_by(StaffMembership.created_at))).all()
    return {
        "items": [
            {
                "id": str(membership.id),
                "name": f"{account.first_name} {account.last_name}".strip(),
                "email": account.email,
                "department_id": membership.department_id,
                "role": membership.role,
                "specialty_id": membership.specialty_id,
                "created_at": membership.created_at,
            }
            for membership, account in rows
        ]
    }


@router.patch("/hospital/staff-membership-requests/{membership_id}")
async def review_staff_membership_request(
    membership_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    reviewer, workspace, _tenant = await require_hospital_membership(
        request, session, roles={"hospital_admin", "department_coordinator"}
    )
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(
            status_code=422, detail="Decision must be APPROVE or REJECT"
        )
    membership = await session.scalar(
        select(StaffMembership)
        .where(
            StaffMembership.id == membership_id,
            StaffMembership.hospital_id == workspace.hospital_id,
        )
        .with_for_update()
    )
    if not membership or (
        workspace.role == "department_coordinator"
        and membership.department_id != workspace.department_id
    ):
        raise HTTPException(
            status_code=404, detail="Membership request not found in this workspace"
        )
    account = await session.get(AuthAccount, membership.user_id)
    application = await session.scalar(
        select(SignupApplication)
        .where(SignupApplication.account_id == membership.user_id)
        .order_by(SignupApplication.submitted_at.desc())
    )
    if decision == "APPROVE":
        (
            membership.verification_status,
            membership.employment_status,
            membership.is_active,
        ) = ("VERIFIED", "ACTIVE", True)
        if account:
            account.is_active = True
        if application:
            previous_status = application.status
            application.status = "ACTIVE"
    else:
        (
            membership.verification_status,
            membership.employment_status,
            membership.is_active,
        ) = ("REJECTED", "REJECTED", False)
        if application:
            previous_status = application.status
            application.status = "REJECTED"
    if application:
        session.add(
            ApplicationReviewHistory(
                signup_application_id=application.id,
                reviewer_account_id=reviewer.id,
                previous_status=previous_status,
                new_status=application.status,
                internal_notes=str(payload.get("reason") or "") or None,
            )
        )
    await session.commit()
    return {
        "id": str(membership.id),
        "verification_status": membership.verification_status,
        "employment_status": membership.employment_status,
        "is_active": membership.is_active,
    }


@router.get("/signup/registered-hospitals")
async def registered_signup_hospitals(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = (
        (
            await session.execute(
                select(Tenant)
                .join(HospitalDepartment, HospitalDepartment.hospital_id == Tenant.id)
                .where(Tenant.status == "ACTIVE", HospitalDepartment.status == "ACTIVE")
                .distinct()
                .order_by(Tenant.name)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {"id": str(item.id), "name": item.name, "location": item.state_location}
            for item in rows
        ]
    }


@router.get("/signup/registered-hospitals/{hospital_id}/departments")
async def registered_signup_departments(
    hospital_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    hospital = await session.scalar(
        select(Tenant).where(Tenant.id == hospital_id, Tenant.status == "ACTIVE")
    )
    if not hospital:
        raise HTTPException(status_code=404, detail="Registered hospital not found")
    rows = (
        (
            await session.execute(
                select(HospitalDepartment)
                .where(
                    HospitalDepartment.hospital_id == hospital_id,
                    HospitalDepartment.status == "ACTIVE",
                )
                .order_by(HospitalDepartment.name)
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {"id": str(item.id), "name": item.name, "code": item.code} for item in rows
        ]
    }


@router.post("/signup/invitations/validate")
async def validate_signup_invitation(
    payload: SignupInvitationValidateRequest, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    invitation = await _validated_invitation(
        session, payload.role, payload.token, payload.email
    )
    assert invitation is not None
    hospital = await session.get(Tenant, invitation.hospital_id)
    return {
        "valid": True,
        "organization_id": str(invitation.organization_id or invitation.hospital_id),
        "hospital_name": hospital.name if hospital else None,
        "department_id": invitation.department_id,
        "intended_role": invitation.intended_role or invitation.permitted_role,
        "specialty_id": invitation.specialty_id,
        "employment_type": invitation.employment_type,
        "expires_at": invitation.expires_at,
    }
