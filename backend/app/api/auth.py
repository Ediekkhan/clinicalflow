from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_pin, issue_patient_token, issue_staff_token, verify_pin
from app.db.session import get_session
from app.models.domain import Patient, Specialist, Staff, Tenant
from app.schemas.synaptiverse import PatientAuthResponse, PatientRead, PatientSignup, PasswordLogin, SpecialistLogin
from app.services.card_generator import generate_card_number
from app.services.lexicon import get_redis


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    role: str = Field(pattern="^(ADMIN|NURSE|MATRON)$")
    pin: str = Field(min_length=4, max_length=4)


class HospitalLoginRequest(BaseModel):
    hospital_code: str = Field(min_length=3)
    password: str = Field(min_length=8)
    staff_role: str = Field(pattern="^(DOCTOR|NURSE|ADMIN)$")
    specialist_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff_id: str
    role: str


@router.post("/pin", response_model=LoginResponse)
async def login_with_pin(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    tenant_id = request.state.tenant_id
    statement = (
        select(Staff)
        .where(Staff.tenant_id == tenant_id)
        .where(Staff.role == payload.role)
        .where(Staff.is_active.is_(True))
        .limit(1)
    )
    staff = (await session.scalars(statement)).first()
    if staff is None or not verify_pin(payload.pin, staff.hashed_pin):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN.")

    return LoginResponse(
        access_token=issue_staff_token(tenant_id, staff.id, staff.role),
        staff_id=str(staff.id),
        role=staff.role,
    )


@router.post("/hospital/login", response_model=LoginResponse)
async def hospital_login(
    payload: HospitalLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Tenant-level login for hospital staff.

    Doctors and specialists do not own a separate clinic. They enter through the
    hospital tenant account, then the UI scopes their patient list by assigned
    specialist ID.
    """

    tenant_id = request.state.tenant_id
    if payload.password != get_settings().hospital_account_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid hospital password.")

    if payload.staff_role == "DOCTOR":
        specialist = (
            await session.scalars(
                select(Specialist)
                .where(Specialist.tenant_id == tenant_id)
                .where(Specialist.is_available.is_(True))
                .limit(1)
            )
        ).first()
        if specialist is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No available doctor profile.")
        return LoginResponse(
            access_token=issue_staff_token(tenant_id, specialist.id, "DOCTOR"),
            staff_id=str(specialist.id),
            role="DOCTOR",
        )

    staff_role = "NURSE" if payload.staff_role == "NURSE" else "ADMIN"
    staff = (
        await session.scalars(
            select(Staff)
            .where(Staff.tenant_id == tenant_id)
            .where(Staff.role == staff_role)
            .where(Staff.is_active.is_(True))
            .limit(1)
        )
    ).first()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active hospital staff profile.")
    return LoginResponse(
        access_token=issue_staff_token(tenant_id, staff.id, staff_role),
        staff_id=str(staff.id),
        role=staff_role,
    )


@router.post("/patient/signup", response_model=PatientAuthResponse)
async def patient_signup(
    payload: PatientSignup,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    tenant_id = request.state.tenant_id
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    existing = (
        await session.scalars(
            select(Patient).where(Patient.tenant_id == tenant_id).where(Patient.phone == payload.phone)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone is already registered.")
    patient = Patient(
        tenant_id=tenant_id,
        full_name=payload.full_name,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        hashed_password=hash_pin(payload.password[-4:].zfill(4)),
        card_number=await generate_card_number(await get_redis(), tenant.state_location, str(tenant_id)),
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    session.add(patient)
    await session.flush()
    return PatientAuthResponse(
        access_token=issue_patient_token(tenant_id, patient.id),
        patient=PatientRead.model_validate(patient),
    )


@router.post("/patient/login", response_model=PatientAuthResponse)
async def patient_login(
    payload: PasswordLogin,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    tenant_id = request.state.tenant_id
    patient = (
        await session.scalars(
            select(Patient)
            .where(Patient.tenant_id == tenant_id)
            .where(Patient.phone == payload.email_or_phone)
        )
    ).first()
    if patient is None or not verify_pin(payload.password[-4:].zfill(4), patient.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return PatientAuthResponse(
        access_token=issue_patient_token(tenant_id, patient.id),
        patient=PatientRead.model_validate(patient),
    )


@router.post("/specialist/login", response_model=LoginResponse)
async def specialist_login(
    payload: SpecialistLogin,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    tenant_id = request.state.tenant_id
    specialist = (
        await session.scalars(
            select(Specialist)
            .where(Specialist.tenant_id == tenant_id)
            .where(Specialist.email == payload.email)
            .where(Specialist.is_available.is_(True))
        )
    ).first()
    if specialist is None or not verify_pin(payload.password[-4:].zfill(4), specialist.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return LoginResponse(
        access_token=issue_staff_token(tenant_id, specialist.id, "SPECIALIST"),
        staff_id=str(specialist.id),
        role="SPECIALIST",
    )
