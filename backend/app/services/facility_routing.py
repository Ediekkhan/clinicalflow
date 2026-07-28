from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FacilityRegistry, FacilityService, OperationalRecord, Provider, ProviderSlot, StaffMembership, Tenant

EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True)
class FacilityCandidate:
    tenant: Tenant
    registry: FacilityRegistry
    eligible: bool
    distance_km: float | None
    suitability_score: float
    has_required_capability: bool
    has_emergency_capability: bool
    has_staff_coverage: bool
    has_capacity: bool
    reasons: tuple[str, ...]
    rank: int | None = None


@dataclass(frozen=True)
class FacilityRoute:
    tenant: Tenant
    slot: ProviderSlot | None
    provider: Provider | None
    distance_km: float
    match_basis: str
    required_service: str
    required_specialty: str
    candidates: tuple[FacilityCandidate, ...]


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
    return (await session.execute(
        select(ProviderSlot, Provider)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(
            ProviderSlot.tenant_id == tenant_id,
            ProviderSlot.is_locked.is_(False),
            ProviderSlot.is_booked.is_(False),
            Provider.is_active.is_(True),
            func.lower(Provider.specialty) == specialty.casefold(),
        )
        .order_by(ProviderSlot.starts_at.asc())
        .limit(1)
    )).one_or_none()


async def _facility_capability(session: AsyncSession, registry: FacilityRegistry, tenant_id: UUID, specialty: str) -> bool:
    normalized = specialty.casefold()
    service = await session.scalar(select(FacilityService.id).where(
        FacilityService.facility_registry_id == registry.id,
        FacilityService.status == "ACTIVE",
        or_(func.lower(FacilityService.specialty_code) == normalized, func.lower(FacilityService.service_code) == normalized),
    ).limit(1))
    provider = await session.scalar(select(Provider.id).where(Provider.tenant_id == tenant_id, Provider.is_active.is_(True), func.lower(Provider.specialty) == normalized).limit(1))
    membership = await session.scalar(select(StaffMembership.id).where(
        StaffMembership.hospital_id == tenant_id,
        StaffMembership.is_active.is_(True),
        StaffMembership.verification_status == "VERIFIED",
        StaffMembership.employment_status == "ACTIVE",
        func.lower(StaffMembership.specialty_id) == normalized,
    ).limit(1))
    return bool(service or provider or membership)


async def _staff_coverage(session: AsyncSession, tenant_id: UUID, specialty: str) -> bool:
    normalized = specialty.casefold()
    slot = await nearest_available_slot(session, tenant_id, specialty)
    membership = await session.scalar(select(StaffMembership.id).where(
        StaffMembership.hospital_id == tenant_id,
        StaffMembership.is_active.is_(True),
        StaffMembership.is_on_duty.is_(True),
        StaffMembership.verification_status == "VERIFIED",
        StaffMembership.employment_status == "ACTIVE",
        func.lower(StaffMembership.specialty_id) == normalized,
    ).limit(1))
    return bool(slot or membership)


async def rank_eligible_facilities(
    session: AsyncSession,
    patient_latitude: float,
    patient_longitude: float,
    clinical_route: Any,
    *,
    preferred_facility_id: UUID | None = None,
) -> tuple[FacilityCandidate, ...]:
    if not valid_coordinates(patient_latitude, patient_longitude):
        return ()
    disabled_rows = await session.execute(select(OperationalRecord.tenant_id).where(
        OperationalRecord.entity == "system",
        OperationalRecord.resource == "settings",
        OperationalRecord.title == "intake_enabled",
        OperationalRecord.status == "DISABLED",
    ))
    disabled_ids = set(disabled_rows.scalars().all())
    rows = (await session.execute(select(Tenant, FacilityRegistry).join(FacilityRegistry, FacilityRegistry.tenant_id == Tenant.id))).all()
    specialty = str(clinical_route.target_specialty or "General Medicine")
    severe = str(clinical_route.derived_urgency).upper() == "CRITICAL"
    candidates: list[FacilityCandidate] = []
    for tenant, registry in rows:
        reasons: list[str] = []
        coordinates_valid = valid_coordinates(tenant.latitude, tenant.longitude)
        distance = haversine_km(patient_latitude, patient_longitude, tenant.latitude, tenant.longitude) if coordinates_valid else None
        capability = await _facility_capability(session, registry, tenant.id, specialty)
        staff_coverage = await _staff_coverage(session, tenant.id, specialty)
        capacity = registry.capacity_status.upper() not in {"FULL", "CLOSED", "UNAVAILABLE"}
        emergency = bool(registry.emergency_capable)
        active = tenant.status == "ACTIVE" and registry.status == "ACTIVE"
        accepting = tenant.accepts_patients and registry.accepts_patients and tenant.id not in disabled_ids
        if not active: reasons.append("Facility is inactive or unverified")
        if not accepting: reasons.append("Facility is not accepting patients")
        if not coordinates_valid: reasons.append("Facility has no valid routing coordinates")
        if not capability: reasons.append(f"Required specialty is unavailable: {specialty}")
        if not staff_coverage: reasons.append(f"No verified on-duty coverage for {specialty}")
        if not capacity: reasons.append("Facility is at capacity")
        if severe and not emergency: reasons.append("Critical cases require emergency capability")
        eligible = active and accepting and coordinates_valid and capability and staff_coverage and capacity and (not severe or emergency)
        score = 0.0
        if eligible:
            score = 100.0 + (30.0 if severe and emergency else 10.0 if emergency else 0.0) + 20.0 + 10.0
            score -= min(distance or 0, 100.0)
            if preferred_facility_id == tenant.id:
                score += 15.0
                reasons.append("Matches patient facility preference")
            reasons.insert(0, f"Clinically suitable for {specialty}")
        candidates.append(FacilityCandidate(tenant=tenant, registry=registry, eligible=eligible, distance_km=distance, suitability_score=round(score, 3), has_required_capability=capability, has_emergency_capability=emergency, has_staff_coverage=staff_coverage, has_capacity=capacity, reasons=tuple(reasons)))
    eligible_sorted = sorted((item for item in candidates if item.eligible), key=lambda item: (-item.suitability_score, item.distance_km or float("inf"), str(item.tenant.id)))
    rank_by_id = {item.tenant.id: index + 1 for index, item in enumerate(eligible_sorted)}
    return tuple(FacilityCandidate(**{**item.__dict__, "rank": rank_by_id.get(item.tenant.id)}) for item in candidates)


async def select_nearest_eligible_hospital(
    session: AsyncSession,
    patient_latitude: float,
    patient_longitude: float,
    clinical_route: Any,
    *,
    preferred_facility_id: UUID | None = None,
) -> FacilityRoute | None:
    candidates = await rank_eligible_facilities(session, patient_latitude, patient_longitude, clinical_route, preferred_facility_id=preferred_facility_id)
    selected = min((item for item in candidates if item.eligible), key=lambda item: (item.rank or 999999, str(item.tenant.id)), default=None)
    if not selected or selected.distance_km is None:
        return None
    specialty = str(clinical_route.target_specialty or "General Medicine")
    slot_row = await nearest_available_slot(session, selected.tenant.id, specialty)
    slot = slot_row[0] if slot_row else None
    provider = slot_row[1] if slot_row else None
    reason = "; ".join(selected.reasons[:2])
    return FacilityRoute(tenant=selected.tenant, slot=slot, provider=provider, distance_km=selected.distance_km, match_basis=reason, required_service=specialty, required_specialty=specialty, candidates=candidates)
