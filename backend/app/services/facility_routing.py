from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OperationalRecord, Provider, ProviderSlot, Tenant

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class FacilityRoute:
    tenant: Tenant
    slot: ProviderSlot | None
    provider: Provider | None
    distance_km: float
    match_basis: str


def valid_coordinates(latitude: float | None, longitude: float | None) -> bool:
    return latitude is not None and longitude is not None and -90 <= latitude <= 90 and -180 <= longitude <= 180


def haversine_km(origin_latitude: float, origin_longitude: float, destination_latitude: float, destination_longitude: float) -> float:
    origin_lat = radians(origin_latitude)
    origin_lng = radians(origin_longitude)
    destination_lat = radians(destination_latitude)
    destination_lng = radians(destination_longitude)
    delta_lat = destination_lat - origin_lat
    delta_lng = destination_lng - origin_lng
    value = sin(delta_lat / 2) ** 2 + cos(origin_lat) * cos(destination_lat) * sin(delta_lng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(value))


async def nearest_available_slot(session: AsyncSession, tenant_id: Any, specialty: str) -> tuple[ProviderSlot, Provider] | None:
    async def fetch(match_specialty: bool) -> tuple[ProviderSlot, Provider] | None:
        filters = [
            ProviderSlot.tenant_id == tenant_id,
            ProviderSlot.is_locked.is_(False),
            ProviderSlot.is_booked.is_(False),
            Provider.is_active.is_(True),
        ]
        if match_specialty:
            filters.append(Provider.specialty == specialty)
        return (await session.execute(
            select(ProviderSlot, Provider)
            .join(Provider, Provider.id == ProviderSlot.provider_id)
            .where(*filters)
            .order_by(ProviderSlot.starts_at.asc())
            .limit(1)
        )).one_or_none()

    return await fetch(True) or await fetch(False)


async def select_nearest_eligible_hospital(
    session: AsyncSession,
    patient_latitude: float,
    patient_longitude: float,
    clinical_route: Any,
) -> FacilityRoute | None:
    if not valid_coordinates(patient_latitude, patient_longitude):
        return None

    disabled_intake_rows = await session.execute(
        select(OperationalRecord.tenant_id).where(
            OperationalRecord.entity == "system",
            OperationalRecord.resource == "settings",
            OperationalRecord.title == "intake_enabled",
            OperationalRecord.status == "DISABLED",
        )
    )
    disabled_tenant_ids = set(disabled_intake_rows.scalars().all())
    tenant_rows = (await session.execute(
        select(Tenant).where(
            Tenant.status == "ACTIVE",
            Tenant.accepts_patients.is_(True),
            Tenant.latitude.is_not(None),
            Tenant.longitude.is_not(None),
        )
    )).scalars().all()

    candidates = [
        (tenant, haversine_km(patient_latitude, patient_longitude, tenant.latitude, tenant.longitude))
        for tenant in tenant_rows
        if tenant.id not in disabled_tenant_ids and valid_coordinates(tenant.latitude, tenant.longitude)
    ]
    if not candidates:
        return None

    tenant, distance_km = min(candidates, key=lambda candidate: (candidate[1], str(candidate[0].id)))
    slot_row = await nearest_available_slot(session, tenant.id, clinical_route.target_specialty)
    slot = slot_row[0] if slot_row else None
    provider = slot_row[1] if slot_row else None
    return FacilityRoute(
        tenant=tenant,
        slot=slot,
        provider=provider,
        distance_km=distance_km,
        match_basis="Nearest active registered hospital by patient coordinates",
    )

