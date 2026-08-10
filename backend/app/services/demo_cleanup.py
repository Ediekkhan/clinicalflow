from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    Appointment,
    AuthAccount,
    Notification,
    OperationalRecord,
    Provider,
    ProviderSlot,
    StaffMembership,
    Tenant,
    Ticket,
)

DEMO_TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
DEMO_IDENTIFIERS = {
    "+2348012345678",
    "dr.ada@example.com",
    "uyo-family:nurse",
    "uyo-family:admin",
    "uyo-family:doctor",
    "uyo-family:hospital_admin",
}


async def build_demo_manifest(session: AsyncSession) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    tenant = await session.get(Tenant, DEMO_TENANT_ID)
    if tenant:
        records.append({"type": "Tenant", "id": str(tenant.id), "reason": "exact legacy demo tenant UUID"})
    accounts = list((await session.execute(select(AuthAccount).where(AuthAccount.identifier.in_(DEMO_IDENTIFIERS)))).scalars())
    records.extend({"type": "AuthAccount", "id": str(row.id), "reason": f"exact legacy identifier:{row.identifier}"} for row in accounts)
    related = {}
    for model, column, label in (
        (StaffMembership, StaffMembership.hospital_id, "staff_memberships"),
        (Provider, Provider.tenant_id, "providers"),
        (ProviderSlot, ProviderSlot.tenant_id, "provider_slots"),
        (Appointment, Appointment.tenant_id, "appointments"),
        (Ticket, Ticket.tenant_id, "tickets"),
        (Notification, Notification.tenant_id, "notifications"),
        (OperationalRecord, OperationalRecord.tenant_id, "operational_records"),
    ):
        related[label] = int(await session.scalar(select(func.count()).select_from(model).where(column == DEMO_TENANT_ID)) or 0)
    body = {
        "environment": settings.environment,
        "database_fingerprint": hashlib.sha256(settings.database_url.encode()).hexdigest()[:16],
        "generated_at": datetime.now(UTC).isoformat(),
        "records": records,
        "related_counts": related,
        "deletion_order": ["notifications", "appointments", "provider_slots", "tickets", "staff_memberships", "providers", "auth_accounts", "tenant"],
        "dry_run_only": True,
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["manifest_id"] = hashlib.sha256(encoded).hexdigest()
    return body


async def dry_run_demo_cleanup(session: AsyncSession) -> dict[str, Any]:
    if settings.environment not in {"test", "development", "staging", "production"}:
        raise ValueError("Refusing cleanup against an unidentified environment")
    manifest = await build_demo_manifest(session)
    return manifest | {"would_delete": len(manifest["records"]), "deleted": 0}
