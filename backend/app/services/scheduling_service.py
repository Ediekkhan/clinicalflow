from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Provider, ProviderSlot
from app.services.auth_service import apply_tenant_context


async def seed_demo_schedule(db: AsyncSession, tenant_id: UUID) -> None:
    await apply_tenant_context(db, tenant_id)
    existing = await db.scalar(select(Provider.id).where(Provider.tenant_id == tenant_id).limit(1))
    if existing:
        return

    providers = [
        Provider(tenant_id=tenant_id, full_name="Dr. Ada Okafor", specialty="General Medicine", room_label="Room 2"),
        Provider(tenant_id=tenant_id, full_name="Dr. Bassey Udo", specialty="Pediatrics", room_label="Room 4"),
        Provider(tenant_id=tenant_id, full_name="Dr. Ifeoma Eze", specialty="Internal Medicine", room_label="Room 6"),
    ]
    db.add_all(providers)
    await db.flush()

    first_day = datetime.combine(datetime.now(UTC).date() + timedelta(days=1), time(hour=8), tzinfo=UTC)
    for day_offset in range(5):
        for provider_index, provider in enumerate(providers):
            for slot_index in range(6):
                starts_at = first_day + timedelta(days=day_offset, minutes=45 * slot_index + 15 * provider_index)
                db.add(ProviderSlot(
                    tenant_id=tenant_id,
                    provider_id=provider.id,
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(minutes=30),
                ))
    await db.commit()
