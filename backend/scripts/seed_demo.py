import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import insert, select

from app.core.config import get_settings
from app.core.security import hash_password, hash_pin
from app.db.session import SessionLocal, set_tenant_context
from app.models.domain import Patient, ProviderSlot, Specialist, Staff, Tenant


async def main() -> None:
    settings = get_settings()
    tenant_id = settings.demo_tenant_id
    async with SessionLocal() as session:
        async with session.begin():
            await set_tenant_context(session, tenant_id)
            exists = await session.scalar(select(Tenant.id).where(Tenant.id == tenant_id))
            if not exists:
                await session.execute(
                    insert(Tenant).values(
                        id=tenant_id,
                        name="Uyo Family Clinic",
                        state_location="Akwa Ibom",
                        address="112 Wellington Bassey Way, Uyo",
                        latitude=5.037739,
                        longitude=7.912795,
                        status="ACTIVE",
                    )
                )
            staff_exists = await session.scalar(select(Staff.id).where(Staff.tenant_id == tenant_id))
            if not staff_exists:
                session.add_all(
                    [
                        Staff(
                            tenant_id=tenant_id,
                            role="NURSE",
                            hashed_pin=hash_pin("4829"),
                            full_name="Nurse Iniobong Akpan",
                        ),
                        Staff(
                            tenant_id=tenant_id,
                            role="ADMIN",
                            hashed_pin=hash_pin("7391"),
                            full_name="Admin Chiamaka Okafor",
                        ),
                    ]
                )
            slot_exists = await session.scalar(
                select(ProviderSlot.id).where(ProviderSlot.tenant_id == tenant_id)
            )
            specialist_exists = await session.scalar(
                select(Specialist.id).where(Specialist.tenant_id == tenant_id)
            )
            if not specialist_exists:
                session.add_all(
                    [
                        Specialist(
                            tenant_id=tenant_id,
                            full_name="Dr. Udo Okon",
                            specialty="General Practitioner",
                            hashed_password=hash_password("DemoPass2026"),
                            phone="+2348090012233",
                            email="dr.udo@synaptiverse.ng",
                        ),
                        Specialist(
                            tenant_id=tenant_id,
                            full_name="Dr. Ada Balogun",
                            specialty="Cardiologist",
                            hashed_password=hash_password("DemoPass2026"),
                            phone="+2348090012244",
                            email="dr.ada@synaptiverse.ng",
                        ),
                    ]
                )
            patient_exists = await session.scalar(select(Patient.id).where(Patient.tenant_id == tenant_id))
            if not patient_exists:
                session.add(
                    Patient(
                        tenant_id=tenant_id,
                        full_name="Kaldera Thomas",
                        phone="+2348012345678",
                        date_of_birth=datetime(1998, 3, 15, tzinfo=UTC).date(),
                        gender="MALE",
                        card_number="SV-AKS-2026-00412",
                        hashed_password=hash_password("DemoPass2026"),
                        latitude=5.0377,
                        longitude=7.9128,
                    )
                )
            if not slot_exists:
                base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                providers = [
                    ("Dr. Ekanem", "General Practice", "Room 2"),
                    ("Dr. Balogun", "Emergency Medicine", "Room 4"),
                    ("Dr. Udo", "Obstetrics", "Room 3"),
                ]
                for day in range(3):
                    for hour in range(8):
                        for provider_name, specialty, room_label in providers:
                            starts = base + timedelta(days=day, hours=hour)
                            session.add(
                                ProviderSlot(
                                    tenant_id=tenant_id,
                                    provider_name=provider_name,
                                    specialty=specialty,
                                    room_label=room_label,
                                    starts_at=starts,
                                    ends_at=starts + timedelta(minutes=30),
                                )
                            )


if __name__ == "__main__":
    asyncio.run(main())
