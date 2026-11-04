from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/staff/workspaces")
async def staff_workspaces(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    if account.role not in {
        "doctor",
        "specialist",
        "nurse",
        "department_coordinator",
        "hospital_admin",
        "admin",
    }:
        raise HTTPException(status_code=403, detail="Staff workspace access required")
    token = (
        request.cookies.get(ACCESS_COOKIE)
        or request.headers.get("authorization", "")[7:].strip()
    )
    authenticated = await account_for_access_token(session, token) if token else None
    selected_id = (
        authenticated[1].selected_membership_id
        if authenticated and authenticated[1]
        else None
    )
    memberships = list(
        (
            await session.execute(
                select(StaffMembership)
                .where(StaffMembership.user_id == account.id)
                .order_by(StaffMembership.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    departments = (
        {
            item.id: item
            for item in (
                await session.execute(
                    select(HospitalDepartment).where(
                        HospitalDepartment.id.in_(
                            [
                                item.department_ref_id
                                for item in memberships
                                if item.department_ref_id
                            ]
                        )
                    )
                )
            )
            .scalars()
            .all()
        }
        if memberships
        else {}
    )
    facilities = (
        {
            item.id: item
            for item in (
                await session.execute(
                    select(Tenant).where(
                        Tenant.id.in_([item.hospital_id for item in memberships])
                    )
                )
            )
            .scalars()
            .all()
        }
        if memberships
        else {}
    )
    now = utc_now()

    def state(membership: StaffMembership) -> str:
        if (
            membership.employment_status == "SUSPENDED"
            or membership.verification_status == "SUSPENDED"
        ):
            return "MEMBERSHIP_SUSPENDED"
        if membership.verification_status in {"PENDING", "PENDING_VERIFICATION"}:
            return "LICENCE_VERIFICATION_REQUIRED"
        if (
            membership.verification_status == "PENDING_HOSPITAL_APPROVAL"
            or membership.employment_status == "PENDING"
        ):
            return "FACILITY_APPROVAL_REQUIRED"
        if (
            not membership.is_active
            or membership.employment_status != "ACTIVE"
            or membership.verification_status != "VERIFIED"
            or membership.active_from.replace(
                tzinfo=membership.active_from.tzinfo or UTC
            )
            > now
            or (
                membership.active_until
                and membership.active_until.replace(
                    tzinfo=membership.active_until.tzinfo or UTC
                )
                < now
            )
        ):
            return "INACTIVE"
        return "MEMBERSHIP_ACTIVE"

    return [
        {
            "id": str(membership.id),
            "hospital_id": str(membership.hospital_id),
            "hospital_name": (
                facilities.get(membership.hospital_id).name
                if facilities.get(membership.hospital_id)
                else None
            ),
            "department_id": (
                str(membership.department_ref_id)
                if membership.department_ref_id
                else membership.department_id
            ),
            "department_name": (
                departments.get(membership.department_ref_id).name
                if departments.get(membership.department_ref_id)
                else membership.department_id
            ),
            "role": membership.role,
            "specialty_id": (
                str(membership.specialty_ref_id)
                if membership.specialty_ref_id
                else membership.specialty_id
            ),
            "verification_status": membership.verification_status,
            "employment_status": membership.employment_status,
            "is_active": membership.is_active,
            "is_on_duty": membership.is_on_duty,
            "state": state(membership),
            "selected": membership.id == selected_id,
        }
        for membership in memberships
    ]


@router.post("/staff/workspaces/{membership_id}/select")
async def select_staff_workspace(
    membership_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    authorization = request.headers.get("authorization", "")
    token = request.cookies.get(ACCESS_COOKIE) or (
        authorization[7:].strip()
        if authorization.lower().startswith("bearer ")
        else None
    )
    authenticated = await account_for_access_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    account, auth_session = authenticated
    now = utc_now()
    membership = await session.scalar(
        select(StaffMembership).where(
            StaffMembership.id == uuid.UUID(membership_id),
            StaffMembership.user_id == account.id,
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
            status_code=403, detail="Staff workspace is not active or verified"
        )
    auth_session.selected_membership_id = membership.id
    await session.commit()
    return {
        "ok": True,
        "selected_membership_id": str(membership.id),
        "hospital_id": str(membership.hospital_id),
        "department_id": (
            str(membership.department_ref_id)
            if membership.department_ref_id
            else membership.department_id
        ),
    }
