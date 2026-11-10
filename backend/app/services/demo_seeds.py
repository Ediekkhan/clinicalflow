"""Test-only demo data builders.

This module is intentionally separate from production authentication and
scheduling services.  The application imports it only inside the fixture gate
used by tests and local development.  Every public seed function also checks
that gate so a production configuration cannot create demo records by
accident.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    AuthAccount,
    FacilityRegistry,
    GovernmentAuthority,
    GovernmentUserScope,
    HospitalDepartment,
    HospitalDoctorMembership,
    PayerOrganization,
    Provider,
    ProviderSlot,
    StaffMembership,
    Tenant,
)
from app.services.auth_service import apply_tenant_context, find_account, hash_password, utc_now


def _require_fixture_mode() -> None:
    if not settings.fixtures_enabled:
        raise RuntimeError("Demo seed functions are available only when test fixtures are enabled")


def department_code(name: str) -> str:
    return name.strip().lower().replace(" ", "-") or "department"


async def ensure_department(db: AsyncSession, tenant_id: UUID, name: str) -> None:
    existing = await db.scalar(
        select(HospitalDepartment).where(
            HospitalDepartment.hospital_id == tenant_id,
            HospitalDepartment.code == department_code(name),
        )
    )
    if not existing:
        db.add(
            HospitalDepartment(
                hospital_id=tenant_id,
                name=name,
                code=department_code(name),
                description=f"{name} department",
                status="ACTIVE",
                capacity=12,
            )
        )


async def ensure_doctor_memberships(db: AsyncSession, tenant_id: UUID, doctor: AuthAccount, provider: Provider) -> None:
    doctor_membership = await db.scalar(
        select(HospitalDoctorMembership).where(
            HospitalDoctorMembership.hospital_id == tenant_id,
            HospitalDoctorMembership.doctor_id == doctor.id,
            HospitalDoctorMembership.specialty_id == provider.specialty,
        )
    )
    if not doctor_membership:
        db.add(
            HospitalDoctorMembership(
                hospital_id=tenant_id,
                doctor_id=doctor.id,
                specialty_id=provider.specialty,
                verification_status="VERIFIED",
                employment_status="ACTIVE",
                is_active=True,
                active_from=datetime.now(UTC) - timedelta(days=1),
            )
        )
    staff_membership = await db.scalar(
        select(StaffMembership).where(
            StaffMembership.hospital_id == tenant_id,
            StaffMembership.user_id == doctor.id,
            StaffMembership.department_id == provider.specialty,
            StaffMembership.role == "doctor",
        )
    )
    if not staff_membership:
        db.add(
            StaffMembership(
                user_id=doctor.id,
                hospital_id=tenant_id,
                department_id=provider.specialty,
                role="doctor",
                specialty_id=provider.specialty,
                verification_status="VERIFIED",
                employment_status="ACTIVE",
                is_active=True,
                is_on_duty=True,
                daily_capacity=provider.max_daily_capacity,
                active_from=datetime.now(UTC) - timedelta(days=1),
            )
        )


async def seed_demo_accounts(db: AsyncSession) -> None:
    """Create deterministic accounts and sector records for tests only."""
    _require_fixture_mode()
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    if not await db.get(Tenant, tenant_id):
        db.add(
            Tenant(
                id=tenant_id,
                name="ClinicalFlow Demo Clinic",
                state_location="Akwa Ibom",
                latitude=5.0380,
                longitude=7.9090,
                accepts_patients=True,
            )
        )
        await db.flush()
    else:
        tenant = await db.get(Tenant, tenant_id)
        if tenant and (tenant.latitude is None or tenant.longitude is None):
            tenant.latitude = 5.0380
            tenant.longitude = 7.9090
            tenant.accepts_patients = True
    seeds = (
        dict(role="patient", identifier="+2348012345678", first_name="Ada", last_name="Okafor", phone="+2348012345678", card_number="SV-1001"),
        dict(role="specialist", identifier="dr.ada@example.com", first_name="Ada", last_name="Okafor", email="dr.ada@example.com", specialty="General Medicine"),
        dict(role="nurse", identifier="uyo-family:nurse", first_name="Ini", last_name="Etim", email="nurse.ini@example.com"),
        dict(role="admin", identifier="uyo-family:admin", first_name="System", last_name="Administrator"),
        dict(role="doctor", identifier="doctor.bassey@example.com", first_name="Bassey", last_name="Udo", email="doctor.bassey@example.com", specialty="General Medicine"),
        dict(role="hospital_admin", identifier="admin.grace@example.com", first_name="Grace", last_name="Akpan", email="admin.grace@example.com"),
    )
    for seed in seeds:
        if not await find_account(db, seed["role"], seed["identifier"], tenant_id):
            credential = {"nurse": "2468", "admin": "1357"}.get(seed["role"], "Password123!")
            db.add(AuthAccount(tenant_id=tenant_id, password_hash=hash_password(credential), **seed))
    await db.flush()
    staff_accounts = list(
        (
            await db.execute(
                select(AuthAccount).where(
                    AuthAccount.tenant_id == tenant_id,
                    AuthAccount.role.in_(["doctor", "specialist", "nurse", "hospital_admin"]),
                )
            )
        )
        .scalars()
        .all()
    )
    for account in staff_accounts:
        department = account.specialty or "General Medicine"
        existing_membership = await db.scalar(
            select(StaffMembership).where(
                StaffMembership.user_id == account.id,
                StaffMembership.hospital_id == tenant_id,
                StaffMembership.department_id == department,
                StaffMembership.role == account.role,
            )
        )
        if not existing_membership:
            db.add(
                StaffMembership(
                    user_id=account.id,
                    hospital_id=tenant_id,
                    department_id=department,
                    role=account.role,
                    specialty_id=account.specialty,
                    verification_status="VERIFIED",
                    employment_status="ACTIVE",
                    is_active=True,
                    is_on_duty=True,
                    active_from=utc_now() - timedelta(days=1),
                )
            )
    sector_fixtures = (
        (UUID("22222222-2222-2222-2222-222222222222"), "ClinicalFlow Test Pharmacy", "pharmacy", "pharmacy@example.com"),
        (UUID("33333333-3333-3333-3333-333333333333"), "ClinicalFlow Test Laboratory", "laboratory", "laboratory@example.com"),
        (UUID("44444444-4444-4444-4444-444444444444"), "ClinicalFlow Test HMO", "hmo", "hmo@example.com"),
        (UUID("55555555-5555-5555-5555-555555555555"), "ClinicalFlow Test Health Authority", "government", "government@example.com"),
    )
    sector_accounts: dict[str, AuthAccount] = {}
    for sector_tenant_id, tenant_name, role, email in sector_fixtures:
        if not await db.get(Tenant, sector_tenant_id):
            db.add(Tenant(id=sector_tenant_id, name=tenant_name, state_location="Test Jurisdiction", status="ACTIVE"))
        account = await db.scalar(
            select(AuthAccount).where(
                AuthAccount.tenant_id == sector_tenant_id,
                AuthAccount.role == role,
                AuthAccount.identifier == email,
            )
        )
        if not account:
            account = AuthAccount(
                tenant_id=sector_tenant_id,
                role=role,
                identifier=email,
                email=email,
                first_name=tenant_name,
                last_name="Operator",
                password_hash=hash_password("Password123!"),
                is_active=True,
            )
            db.add(account)
            await db.flush()
        sector_accounts[role] = account
    pharmacy_id, laboratory_id, payer_id, government_id = [item[0] for item in sector_fixtures]
    if not await db.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == pharmacy_id)):
        db.add(FacilityRegistry(tenant_id=pharmacy_id, facility_type="PHARMACY", country="NG", jurisdiction="NG-AK", status="ACTIVE", accepts_patients=False))
    if not await db.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == laboratory_id)):
        db.add(FacilityRegistry(tenant_id=laboratory_id, facility_type="LABORATORY", country="NG", jurisdiction="NG-AK", status="ACTIVE", accepts_patients=False))
    if not await db.scalar(select(PayerOrganization).where(PayerOrganization.tenant_id == payer_id)):
        db.add(PayerOrganization(tenant_id=payer_id, country_code="NG", payer_type="HMO", legal_name="ClinicalFlow Test HMO", status="ACTIVE"))
    authority = await db.scalar(select(GovernmentAuthority).where(GovernmentAuthority.tenant_id == government_id))
    if not authority:
        authority = GovernmentAuthority(tenant_id=government_id, country_code="NG", jurisdiction_code="NG-AK", authority_level="STATE", status="ACTIVE")
        db.add(authority)
        await db.flush()
    government_account = sector_accounts["government"]
    if not await db.scalar(select(GovernmentUserScope).where(GovernmentUserScope.user_id == government_account.id, GovernmentUserScope.jurisdiction_code == "NG-AK")):
        db.add(GovernmentUserScope(user_id=government_account.id, authority_id=authority.id, jurisdiction_code="NG-AK", geographic_level="STATE", status="ACTIVE"))
    await db.commit()


async def seed_demo_schedule(db: AsyncSession, tenant_id: UUID) -> None:
    """Create deterministic providers and appointment slots for tests only."""
    _require_fixture_mode()
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
        has_seeded_slot = await db.scalar(select(ProviderSlot.id).where(ProviderSlot.provider_id == provider.id).limit(1))
        if has_seeded_slot:
            continue
        for day_offset in range(5):
            for slot_index in range(6):
                starts_at = first_day + timedelta(days=day_offset, minutes=45 * slot_index + 15 * provider_index)
                db.add(ProviderSlot(tenant_id=tenant_id, provider_id=provider.id, starts_at=starts_at, ends_at=starts_at + timedelta(minutes=30)))
    await db.commit()
