from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthAccount, HospitalDepartment, HospitalDoctorMembership, Provider, ProviderSlot, StaffMembership
from app.services.auth_service import apply_tenant_context


def department_code(name: str) -> str:
    return name.strip().lower().replace(" ", "-") or "department"


async def ensure_department(db: AsyncSession, tenant_id: UUID, name: str) -> None:
    existing = await db.scalar(select(HospitalDepartment).where(HospitalDepartment.hospital_id == tenant_id, HospitalDepartment.code == department_code(name)))
    if not existing:
        db.add(HospitalDepartment(hospital_id=tenant_id, name=name, code=department_code(name), description=f"{name} department", status="ACTIVE", capacity=12))


async def ensure_doctor_memberships(db: AsyncSession, tenant_id: UUID, doctor: AuthAccount, provider: Provider) -> None:
    doctor_membership = await db.scalar(select(HospitalDoctorMembership).where(HospitalDoctorMembership.hospital_id == tenant_id, HospitalDoctorMembership.doctor_id == doctor.id, HospitalDoctorMembership.specialty_id == provider.specialty))
    if not doctor_membership:
        db.add(HospitalDoctorMembership(hospital_id=tenant_id, doctor_id=doctor.id, specialty_id=provider.specialty, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, active_from=datetime.now(UTC) - timedelta(days=1)))
    staff_membership = await db.scalar(select(StaffMembership).where(StaffMembership.hospital_id == tenant_id, StaffMembership.user_id == doctor.id, StaffMembership.department_id == provider.specialty, StaffMembership.role == "doctor"))
    if not staff_membership:
        db.add(StaffMembership(user_id=doctor.id, hospital_id=tenant_id, department_id=provider.specialty, role="doctor", specialty_id=provider.specialty, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, daily_capacity=provider.max_daily_capacity, active_from=datetime.now(UTC) - timedelta(days=1)))


async def seed_demo_schedule(db: AsyncSession, tenant_id: UUID) -> None:
    await apply_tenant_context(db, tenant_id)
    doctor = await db.scalar(select(AuthAccount).where(AuthAccount.tenant_id == tenant_id, AuthAccount.role == "doctor", AuthAccount.is_active.is_(True)).limit(1))
    desired = [
        ("Demo General Medicine Doctor", "General Medicine", "Room 2"),
        ("Demo Pediatrics Doctor", "Pediatrics", "Room 4"),
        ("Demo Internal Medicine Doctor", "Internal Medicine", "Room 6"),
        ("Demo Emergency Medicine Doctor", "Emergency Medicine", "Emergency Room"),
    ]
    providers = list((await db.execute(select(Provider).where(Provider.tenant_id == tenant_id))).scalars().all())
    by_specialty = {provider.specialty: provider for provider in providers}
    for full_name, specialty, room_label in desired:
        if specialty not in by_specialty:
            provider = Provider(tenant_id=tenant_id, doctor_id=doctor.id if doctor else None, full_name=full_name, specialty=specialty, room_label=room_label)
            db.add(provider)
            await db.flush()
            providers.append(provider)
            by_specialty[specialty] = provider
    first_day = datetime.combine(datetime.now(UTC).date() + timedelta(days=1), time(hour=8), tzinfo=UTC)
    for provider_index, provider in enumerate(providers):
        await ensure_department(db, tenant_id, provider.specialty)
        if doctor:
            if provider.doctor_id is None:
                provider.doctor_id = doctor.id
            await ensure_doctor_memberships(db, tenant_id, doctor, provider)
        # Availability state must not cause duplicate seed rows once all slots are booked.
        has_seeded_slot = await db.scalar(select(ProviderSlot.id).where(ProviderSlot.provider_id == provider.id).limit(1))
        if has_seeded_slot:
            continue
        for day_offset in range(5):
            for slot_index in range(6):
                starts_at = first_day + timedelta(days=day_offset, minutes=45 * slot_index + 15 * provider_index)
                db.add(ProviderSlot(tenant_id=tenant_id, provider_id=provider.id, starts_at=starts_at, ends_at=starts_at + timedelta(minutes=30)))
    await db.commit()
