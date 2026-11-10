from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/me")
async def hospital_profile(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, membership, tenant = await require_hospital_membership(request, session)
    profile = _build_profile(account).model_dump()
    profile.update(
        {
            "user_id": str(account.id),
            "membership_id": str(membership.id),
            "hospital_id": str(membership.hospital_id),
            "hospital_name": tenant.name if tenant else None,
            "name": tenant.name if tenant else profile.get("full_name"),
            "location": tenant.state_location if tenant else None,
            "department_id": membership.department_id,
            "department_name": membership.department_id,
            "role": membership.role,
            "specialty": membership.specialty_id or profile.get("specialty"),
            "verification_status": membership.verification_status,
            "employment_status": membership.employment_status,
        }
    )
    return profile


@router.get("/hospital/patients")
async def hospital_patients(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, membership, tenant = await require_hospital_membership(request, session)
    return {
        "identity": {
            "name": tenant.name if tenant else "Hospital",
            "location": tenant.state_location if tenant else None,
            "account_type": membership.role,
        },
        "items": await hospital_ticket_items(session, membership.hospital_id),
    }
