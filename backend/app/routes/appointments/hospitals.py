from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/appointment-slots", response_model=list[SlotResponse])
async def hospital_appointment_slots(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[SlotResponse]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    rows = list(
        (
            await session.execute(
                select(ProviderSlot, Provider, StaffMembership)
                .join(Provider, Provider.id == ProviderSlot.provider_id)
                .join(
                    StaffMembership,
                    (StaffMembership.user_id == Provider.doctor_id)
                    & (StaffMembership.hospital_id == ProviderSlot.tenant_id)
                    & (StaffMembership.specialty_id == Provider.specialty),
                )
                .where(
                    ProviderSlot.tenant_id == membership.hospital_id,
                    Provider.is_active.is_(True),
                    StaffMembership.is_active.is_(True),
                    StaffMembership.verification_status == "VERIFIED",
                    StaffMembership.employment_status == "ACTIVE",
                )
                .order_by(ProviderSlot.starts_at.asc())
            )
        ).all()
    )
    return [
        SlotResponse(
            id=slot.id,
            tenant_id=slot.tenant_id,
            provider_name=provider.full_name,
            specialty=provider.specialty,
            room_label=provider.room_label,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            is_locked=slot.is_locked,
            lock_reason=slot.lock_reason,
            is_booked=slot.is_booked,
        )
        for slot, provider, _staff in rows
    ]


@router.get("/hospital/appointments", response_model=list[AppointmentResponse])
async def hospital_appointments(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[AppointmentResponse]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    result = await session.execute(
        select(Appointment)
        .where(Appointment.hospital_id == membership.hospital_id)
        .order_by(Appointment.created_at.desc())
        .limit(100)
    )
    return [
        await appointment_response(session, appointment)
        for appointment in result.scalars().all()
    ]
