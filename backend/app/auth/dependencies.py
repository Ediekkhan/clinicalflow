from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import ACCESS_COOKIE, verify_token
from app.db.session import get_session
from app.models.domain import Patient, Specialist, Staff


def _extract_access_token(request: Request) -> str | None:
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        return token
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization.split(" ", 1)[1]
    return None


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


async def _payload_for_type(request: Request, expected_type: str) -> dict:
    token = _extract_access_token(request)
    if not token:
        raise _unauthorized()
    payload = verify_token(token)
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    request.state.user = payload
    request.state.user_type = payload.get("type")
    request.state.tenant_id = payload.get("tenant_id")
    return payload


async def get_current_patient(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Patient:
    payload = await _payload_for_type(request, "PATIENT")
    patient = await db.get(Patient, UUID(payload["sub"]))
    if patient is None:
        raise _unauthorized()
    request.state.patient_id = str(patient.id)
    request.state.tenant_id = str(patient.tenant_id)
    return patient


async def get_current_specialist(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Specialist:
    payload = await _payload_for_type(request, "SPECIALIST")
    specialist = await db.get(Specialist, UUID(payload["sub"]))
    if specialist is None or not specialist.is_available:
        raise _unauthorized()
    request.state.specialist_id = str(specialist.id)
    request.state.tenant_id = str(specialist.tenant_id)
    return specialist


async def get_current_staff(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Staff:
    payload = await _payload_for_type(request, "STAFF")
    staff = (
        await db.scalars(
            select(Staff)
            .where(Staff.id == UUID(payload["sub"]))
            .where(Staff.is_active.is_(True))
        )
    ).first()
    if staff is None or staff.is_locked:
        raise _unauthorized()
    await db.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(staff.tenant_id)},
    )
    request.state.staff_id = str(staff.id)
    request.state.staff_role = staff.role
    request.state.tenant_id = str(staff.tenant_id)
    return staff


async def require_admin(
    staff: Staff = Depends(get_current_staff),
) -> Staff:
    if staff.role != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return staff

