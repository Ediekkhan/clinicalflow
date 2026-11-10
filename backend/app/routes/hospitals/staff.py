from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/specialists")
async def hospital_specialists(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, membership, tenant = await require_hospital_membership(request, session)
    return {
        "identity": {
            "name": tenant.name if tenant else "Hospital",
            "location": tenant.state_location if tenant else None,
            "account_type": membership.role,
        },
        "items": await hospital_specialist_items(session, membership.hospital_id),
    }


@router.get("/hospital/readiness")
async def hospital_readiness(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    tenant = await session.get(Tenant, account.tenant_id)
    facility = await session.scalar(
        select(FacilityRegistry).where(FacilityRegistry.tenant_id == account.tenant_id)
    )
    departments = await session.scalar(
        select(func.count())
        .select_from(HospitalDepartment)
        .where(
            HospitalDepartment.hospital_id == account.tenant_id,
            HospitalDepartment.status == "ACTIVE",
        )
    )
    staff = await session.scalar(
        select(func.count())
        .select_from(StaffMembership)
        .where(
            StaffMembership.hospital_id == account.tenant_id,
            StaffMembership.is_active.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.role.in_({"doctor", "specialist", "nurse"}),
        )
    )
    services = (
        await session.scalar(
            select(func.count())
            .select_from(FacilityService)
            .where(
                FacilityService.facility_registry_id == facility.id,
                FacilityService.status == "ACTIVE",
            )
        )
        if facility
        else 0
    )
    checks = {
        "location": bool(
            tenant and tenant.latitude is not None and tenant.longitude is not None
        ),
        "departments": bool(departments),
        "services": bool(services),
        "verified_staff": bool(staff),
        "accepts_patients": bool(facility and facility.accepts_patients),
    }
    return {
        "status": "READY" if all(checks.values()) else "SETUP_REQUIRED",
        "checks": checks,
    }


@router.post("/hospital/readiness/submit")
async def submit_hospital_readiness(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    readiness = await hospital_readiness(request, session)
    if readiness["status"] != "READY":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Complete the hospital setup checklist before submitting",
                "checks": readiness["checks"],
            },
        )
    case = await session.scalar(
        select(FacilityVerificationCase)
        .join(
            SignupApplication,
            SignupApplication.id == FacilityVerificationCase.signup_application_id,
        )
        .where(SignupApplication.account_id == account.id)
        .with_for_update()
    )
    if case:
        case.status = "READINESS_REVIEW"
    await session.commit()
    return {"status": "READINESS_REVIEW"}
