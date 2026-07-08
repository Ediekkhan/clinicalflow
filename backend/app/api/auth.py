from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_patient, get_current_specialist
from app.auth.jwt_handler import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    delete_refresh_token,
    revoke_token,
    set_auth_cookies,
    verify_refresh_token,
    verify_token,
)
from app.auth.password_handler import hash_password, verify_password
from app.auth.pin_handler import verify_pin
from app.core.config import get_settings
from app.db.session import SessionLocal, get_session, set_tenant_context
from app.middleware.rate_limit_config import RATE_LIMITS
from app.middleware.rate_limiter import (
    check_rate_limit,
    clear_failed_login,
    get_rate_limit_identifier,
    track_failed_login,
)
from app.models.domain import Appointment, Patient, Specialist, Staff, Tenant, Ticket
from app.schemas.patient import PatientLoginSchema, PatientSignupSchema, SpecialistLoginSchema, StaffLoginSchema
from app.schemas.synaptiverse import PatientRead, SpecialistRead, SynTicketRead
from app.services.audit_service import AuditAction, write_audit_log
from app.services.card_generator import generate_card_number
from app.services.lexicon import get_redis


router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def _write_failed_audit(
    request: Request,
    action: AuditAction,
    actor_type: str,
    tenant_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    async with SessionLocal() as session:
        if tenant_id:
            await set_tenant_context(session, tenant_id)
        await write_audit_log(
            db=session,
            action=action,
            actor_id=None,
            actor_type=actor_type,
            tenant_id=tenant_id,
            ip_address=_client_ip(request),
            metadata=metadata,
            user_agent=_user_agent(request),
        )
        await session.commit()


def _patient_payload(patient: Patient) -> dict:
    return PatientRead.model_validate(patient).model_dump(mode="json")


def _specialist_payload(specialist: Specialist) -> dict:
    return SpecialistRead.model_validate(specialist).model_dump(mode="json")


@router.post("/patient/signup")
async def patient_signup(
    payload: PatientSignupSchema,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    config = RATE_LIMITS["auth:patient:signup"]
    await check_rate_limit(
        key="auth:patient:signup",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )

    settings = get_settings()
    tenant_id = UUID(request.headers.get("X-Tenant-Id") or str(settings.demo_tenant_id))
    await set_tenant_context(session, tenant_id)
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None or tenant.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active clinic not found")

    existing = (
        await session.scalars(
            select(Patient)
            .where(Patient.tenant_id == tenant_id)
            .where(Patient.phone == payload.phone)
            .limit(1)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone is already registered")

    lat = payload.latitude if payload.latitude is not None else payload.lat
    lng = payload.longitude if payload.longitude is not None else payload.lng
    patient = Patient(
        tenant_id=tenant_id,
        full_name=payload.full_name,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        hashed_password=hash_password(payload.password),
        card_number=await generate_card_number(await get_redis(), tenant.state_location, str(tenant_id)),
        latitude=lat,
        longitude=lng,
    )
    session.add(patient)
    await session.flush()

    await write_audit_log(
        db=session,
        action=AuditAction.PATIENT_SIGNUP,
        actor_id=str(patient.id),
        actor_type="PATIENT",
        tenant_id=str(tenant_id),
        ip_address=_client_ip(request),
        resource_type="PATIENT",
        resource_id=str(patient.id),
        metadata={"phone": patient.phone},
        user_agent=_user_agent(request),
    )

    access_token = create_access_token(
        subject=str(patient.id),
        user_type="PATIENT",
        extra_claims={"tenant_id": str(tenant_id)},
        expires_delta=timedelta(hours=8),
    )
    refresh_token = create_refresh_token(str(patient.id), "PATIENT")
    set_auth_cookies(
        response,
        access_token,
        refresh_token,
        access_max_age=8 * 60 * 60,
        refresh_max_age=30 * 24 * 60 * 60,
    )
    return {
        "patient": _patient_payload(patient),
        "card_number": patient.card_number,
        "message": "Patient account created successfully",
    }


@router.post("/patient/login")
async def patient_login(
    payload: PatientLoginSchema,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    config = RATE_LIMITS["auth:patient:login"]
    await check_rate_limit(
        key="auth:patient:login",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )
    await session.execute(text("SET LOCAL app.auth_flow = 'LOGIN'"))
    patient = (
        await session.scalars(select(Patient).where(Patient.phone == payload.phone).limit(1))
    ).first()
    failed_identifier = f"phone:{payload.phone}"
    if patient is None or not verify_password(payload.password, patient.hashed_password):
        await _write_failed_audit(
            request,
            AuditAction.FAILED_LOGIN,
            "PATIENT",
            tenant_id=str(patient.tenant_id) if patient else None,
            metadata={"phone": payload.phone},
        )
        await track_failed_login(failed_identifier)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await clear_failed_login(failed_identifier)
    await set_tenant_context(session, patient.tenant_id)
    access_token = create_access_token(
        subject=str(patient.id),
        user_type="PATIENT",
        extra_claims={"tenant_id": str(patient.tenant_id)},
        expires_delta=timedelta(hours=8),
    )
    refresh_token = create_refresh_token(str(patient.id), "PATIENT")
    set_auth_cookies(
        response,
        access_token,
        refresh_token,
        access_max_age=8 * 60 * 60,
        refresh_max_age=30 * 24 * 60 * 60,
    )
    await write_audit_log(
        db=session,
        action=AuditAction.PATIENT_LOGIN,
        actor_id=str(patient.id),
        actor_type="PATIENT",
        tenant_id=str(patient.tenant_id),
        ip_address=_client_ip(request),
        metadata={"phone": patient.phone},
        user_agent=_user_agent(request),
    )
    return {"patient": _patient_payload(patient)}


@router.get("/patient/me")
async def patient_me(
    request: Request,
    current_patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_session),
):
    latest_ticket = (
        await session.scalars(
            select(Ticket)
            .where(Ticket.patient_id == current_patient.id)
            .order_by(Ticket.created_at.desc())
            .limit(1)
        )
    ).first()
    await write_audit_log(
        db=session,
        action=AuditAction.PATIENT_RECORD_VIEWED,
        actor_id=str(current_patient.id),
        actor_type="PATIENT",
        tenant_id=str(current_patient.tenant_id),
        ip_address=_client_ip(request),
        resource_type="PATIENT",
        resource_id=str(current_patient.id),
        user_agent=_user_agent(request),
    )
    return {
        "patient": _patient_payload(current_patient),
        "card_number": current_patient.card_number,
        "latest_ticket": SynTicketRead.model_validate(latest_ticket).model_dump(mode="json")
        if latest_ticket
        else None,
    }


@router.post("/specialist/login")
async def specialist_login(
    payload: SpecialistLoginSchema,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    config = RATE_LIMITS["auth:specialist:login"]
    await check_rate_limit(
        key="auth:specialist:login",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )
    await session.execute(text("SET LOCAL app.auth_flow = 'LOGIN'"))
    specialist = (
        await session.scalars(select(Specialist).where(Specialist.email == payload.email).limit(1))
    ).first()
    failed_identifier = f"email:{payload.email}"
    if specialist is None or not verify_password(payload.password, specialist.hashed_password):
        await _write_failed_audit(
            request,
            AuditAction.FAILED_LOGIN,
            "SPECIALIST",
            tenant_id=str(specialist.tenant_id) if specialist else None,
            metadata={"email": payload.email},
        )
        await track_failed_login(failed_identifier)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await clear_failed_login(failed_identifier)
    await set_tenant_context(session, specialist.tenant_id)
    extra_claims = {
        "tenant_id": str(specialist.tenant_id),
        "specialty": specialist.specialty,
        "is_available": specialist.is_available,
    }
    access_token = create_access_token(
        subject=str(specialist.id),
        user_type="SPECIALIST",
        extra_claims=extra_claims,
        expires_delta=timedelta(hours=12),
    )
    refresh_token = create_refresh_token(str(specialist.id), "SPECIALIST")
    set_auth_cookies(
        response,
        access_token,
        refresh_token,
        access_max_age=12 * 60 * 60,
        refresh_max_age=7 * 24 * 60 * 60,
    )

    today = datetime.now(UTC).date()
    day_start = datetime.combine(today, time.min, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    appointment_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.specialist_id == specialist.id)
            .where(Appointment.slot_start >= day_start)
            .where(Appointment.slot_start < day_end)
        )
        or 0
    )
    await write_audit_log(
        db=session,
        action=AuditAction.SPECIALIST_LOGIN,
        actor_id=str(specialist.id),
        actor_type="SPECIALIST",
        tenant_id=str(specialist.tenant_id),
        ip_address=_client_ip(request),
        metadata={"email": payload.email, "specialty": specialist.specialty},
        user_agent=_user_agent(request),
    )
    return {"specialist": _specialist_payload(specialist), "today_appointment_count": appointment_count}


@router.get("/specialist/me")
async def specialist_me(
    current_specialist: Specialist = Depends(get_current_specialist),
    session: AsyncSession = Depends(get_session),
):
    today = datetime.now(UTC).date()
    day_start = datetime.combine(today, time.min, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    appointment_count = int(
        await session.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.specialist_id == current_specialist.id)
            .where(Appointment.slot_start >= day_start)
            .where(Appointment.slot_start < day_end)
        )
        or 0
    )
    return {"specialist": _specialist_payload(current_specialist), "today_appointment_count": appointment_count}


@router.get("/clinics")
async def active_clinics(session: AsyncSession = Depends(get_session)):
    await session.execute(text("SET LOCAL app.auth_flow = 'LOGIN'"))
    clinics = (
        await session.scalars(
            select(Tenant).where(Tenant.status == "ACTIVE").order_by(Tenant.name.asc())
        )
    ).all()
    return [
        {"id": str(clinic.id), "name": clinic.name, "state_location": clinic.state_location}
        for clinic in clinics
    ]


@router.get("/clinics/{tenant_id}/staff")
async def active_staff_for_clinic(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    await set_tenant_context(session, tenant_id)
    staff = (
        await session.scalars(
            select(Staff)
            .where(Staff.tenant_id == tenant_id)
            .where(Staff.is_active.is_(True))
            .where(Staff.is_locked.is_(False))
            .order_by(Staff.full_name.asc())
        )
    ).all()
    return [
        {"id": str(member.id), "first_name": member.full_name.split()[0], "role": member.role}
        for member in staff
    ]


@router.post("/staff/login")
async def staff_login(
    payload: StaffLoginSchema,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    config = RATE_LIMITS["auth:staff:login"]
    await check_rate_limit(
        key="auth:staff:login",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )
    await set_tenant_context(session, payload.tenant_id)
    staff = (
        await session.scalars(
            select(Staff)
            .where(Staff.id == payload.staff_id)
            .where(Staff.tenant_id == payload.tenant_id)
            .where(Staff.is_active.is_(True))
            .limit(1)
        )
    ).first()
    if staff is None:
        await _write_failed_audit(
            request,
            AuditAction.FAILED_LOGIN,
            "STAFF",
            tenant_id=str(payload.tenant_id),
            metadata={"staff_id": str(payload.staff_id)},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    redis_client = await get_redis()
    attempts_key = f"pin_attempts:{staff.id}"
    attempts = int(await redis_client.get(attempts_key) or 0) if redis_client else staff.failed_pin_attempts
    if staff.is_locked or attempts >= 5:
        await _write_failed_audit(
            request,
            AuditAction.ACCOUNT_LOCKED,
            "STAFF",
            tenant_id=str(staff.tenant_id),
            metadata={"staff_id": str(staff.id)},
        )
        raise HTTPException(status_code=423, detail="Account locked. Contact admin.")

    if not verify_pin(payload.pin, staff.hashed_pin):
        if redis_client:
            attempts = int(await redis_client.incr(attempts_key))
            await redis_client.expire(attempts_key, 1800)
        else:
            attempts = staff.failed_pin_attempts + 1
        staff.failed_pin_attempts = attempts
        action = AuditAction.FAILED_LOGIN
        status_code = status.HTTP_401_UNAUTHORIZED
        detail = "Invalid credentials"
        if attempts >= 5:
            staff.is_locked = True
            staff.locked_at = datetime.now(UTC)
            action = AuditAction.ACCOUNT_LOCKED
            status_code = 423
            detail = "Account locked. Contact admin."
        await write_audit_log(
            db=session,
            action=action,
            actor_id=str(staff.id),
            actor_type="STAFF",
            tenant_id=str(staff.tenant_id),
            ip_address=_client_ip(request),
            metadata={"failed_pin_attempts": attempts},
            user_agent=_user_agent(request),
        )
        await session.commit()
        raise HTTPException(status_code=status_code, detail=detail)

    if redis_client:
        await redis_client.delete(attempts_key)
    staff.failed_pin_attempts = 0
    access_token = create_access_token(
        subject=str(staff.id),
        user_type="STAFF",
        extra_claims={"tenant_id": str(staff.tenant_id), "role": staff.role},
        expires_delta=timedelta(hours=8),
    )
    set_auth_cookies(response, access_token, access_max_age=8 * 60 * 60)
    tenant = await session.get(Tenant, staff.tenant_id)
    await write_audit_log(
        db=session,
        action=AuditAction.STAFF_LOGIN,
        actor_id=str(staff.id),
        actor_type="STAFF",
        tenant_id=str(staff.tenant_id),
        ip_address=_client_ip(request),
        metadata={"role": staff.role},
        user_agent=_user_agent(request),
    )
    return {
        "staff": {
            "id": str(staff.id),
            "full_name": staff.full_name,
            "first_name": staff.full_name.split()[0],
            "role": staff.role,
        },
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "state_location": tenant.state_location,
        }
        if tenant
        else None,
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        payload = verify_token(token)
        revoke_token(payload["jti"])
        await write_audit_log(
            db=session,
            action=AuditAction.TOKEN_REVOKED,
            actor_id=payload.get("sub"),
            actor_type=payload.get("type", "SYSTEM"),
            tenant_id=payload.get("tenant_id"),
            ip_address=_client_ip(request),
            metadata={"jti": payload.get("jti"), "event": "LOGOUT"},
            user_agent=_user_agent(request),
        )
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    config = RATE_LIMITS["auth:refresh"]
    await check_rate_limit(
        key="auth:refresh",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    payload = verify_refresh_token(token)
    delete_refresh_token(payload["jti"])
    user_type = payload["type"]

    if user_type == "PATIENT":
        patient = await session.get(Patient, UUID(payload["sub"]))
        if patient is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient not found")
        extra_claims = {"tenant_id": str(patient.tenant_id)}
        access_max_age = 8 * 60 * 60
        refresh_max_age = 30 * 24 * 60 * 60
        expires_delta = timedelta(hours=8)
    elif user_type == "SPECIALIST":
        specialist = await session.get(Specialist, UUID(payload["sub"]))
        if specialist is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Specialist not found")
        extra_claims = {
            "tenant_id": str(specialist.tenant_id),
            "specialty": specialist.specialty,
            "is_available": specialist.is_available,
        }
        access_max_age = 12 * 60 * 60
        refresh_max_age = 7 * 24 * 60 * 60
        expires_delta = timedelta(hours=12)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Staff sessions cannot be refreshed")

    access_token = create_access_token(
        subject=payload["sub"],
        user_type=user_type,
        extra_claims=extra_claims,
        expires_delta=expires_delta,
    )
    refresh_token = create_refresh_token(payload["sub"], user_type)
    set_auth_cookies(response, access_token, refresh_token, access_max_age, refresh_max_age)
    return {"message": "Session refreshed"}
