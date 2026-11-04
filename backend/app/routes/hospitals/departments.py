from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/departments")
async def hospital_departments(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, membership, tenant = await require_hospital_membership(request, session)
    return {
        "identity": {
            "name": tenant.name if tenant else "Hospital",
            "location": tenant.state_location if tenant else None,
            "account_type": membership.role,
        },
        "items": await hospital_department_items(session, membership.hospital_id),
    }


@router.get("/hospital/departments/{department_id}")
async def hospital_department_detail(
    department_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    departments = await hospital_department_items(session, membership.hospital_id)
    match = next(
        (
            department
            for department in departments
            if department["id"] == department_id
            or department["code"] == department_id
            or department["name"] == department_id
        ),
        None,
    )
    if not match:
        raise HTTPException(status_code=404, detail="Department not found")
    return match


@router.get("/hospital/departments/{department_id}/available-doctors")
async def hospital_department_available_doctors(
    department_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    departments = await hospital_department_items(session, membership.hospital_id)
    match = next(
        (
            department
            for department in departments
            if department["id"] == department_id
            or department["code"] == department_id
            or department["name"] == department_id
        ),
        None,
    )
    if not match:
        raise HTTPException(status_code=404, detail="Department not found")
    doctors = match.get("available_doctors_list")
    available_doctors = doctors if isinstance(doctors, list) else []
    return {
        "items": [
            doctor
            for doctor in available_doctors
            if doctor.get("availability") == "AVAILABLE"
        ]
    }
