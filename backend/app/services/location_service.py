from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Specialist, Tenant
from app.schemas.synaptiverse import ClinicMatch


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * radius * asin(sqrt(a))


async def nearby_clinics(
    session: AsyncSession,
    latitude: float,
    longitude: float,
    specialty: str,
    urgency: str,
) -> list[ClinicMatch]:
    tenants = list(
        (
            await session.scalars(
                select(Tenant)
                .where(Tenant.status == "ACTIVE")
                .where(Tenant.latitude.is_not(None))
                .where(Tenant.longitude.is_not(None))
            )
        ).all()
    )
    specialists = list((await session.scalars(select(Specialist).where(Specialist.is_available.is_(True)))).all())
    by_tenant: dict[UUID, list[Specialist]] = {}
    for specialist in specialists:
        by_tenant.setdefault(specialist.tenant_id, []).append(specialist)

    matches: list[ClinicMatch] = []
    for tenant in tenants:
        clinic_specialists = by_tenant.get(tenant.id, [])
        specialty_matches = [item for item in clinic_specialists if item.specialty == specialty]
        candidates = clinic_specialists if urgency == "CRITICAL" else specialty_matches
        if not candidates:
            continue
        selected = candidates[0]
        matches.append(
            ClinicMatch(
                clinic_id=tenant.id,
                clinic_name=tenant.name,
                address=tenant.address,
                distance_km=round(
                    haversine_km(
                        latitude,
                        longitude,
                        float(tenant.latitude or 0),
                        float(tenant.longitude or 0),
                    ),
                    2,
                ),
                available_slots=6,
                specialist_id=selected.id,
                specialist_name=selected.full_name,
            )
        )

    limit = 1 if urgency == "CRITICAL" else 3 if urgency == "URGENT" else 5
    return sorted(matches, key=lambda item: item.distance_km)[:limit]

