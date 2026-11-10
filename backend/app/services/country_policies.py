from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CountryPolicy:
    code: str
    emergency_number: str
    emergency_language: str
    routine_radius_km: float
    urgent_radius_km: float
    critical_radius_km: float
    timezone: str
    measurement_system: str = "metric"


COUNTRY_POLICIES = {
    "NG": CountryPolicy("NG", "112", "en", 100.0, 75.0, 40.0, "Africa/Lagos"),
    "US": CountryPolicy("US", "911", "en", 150.0, 100.0, 50.0, "America/New_York", "imperial"),
    "CA": CountryPolicy("CA", "911", "en", 150.0, 100.0, 50.0, "America/Toronto", "metric"),
    "GB": CountryPolicy("GB", "999 or 112", "en", 100.0, 75.0, 40.0, "Europe/London"),
    "GH": CountryPolicy("GH", "112", "en", 100.0, 75.0, 40.0, "Africa/Accra"),
    "KE": CountryPolicy("KE", "999 or 112", "en", 100.0, 75.0, 40.0, "Africa/Nairobi"),
}


def country_policy(code: str | None) -> CountryPolicy | None:
    return COUNTRY_POLICIES.get(str(code or "").strip().upper())


def radius_for_urgency(code: str, urgency: str) -> float | None:
    policy = country_policy(code)
    if not policy:
        return None
    return {"CRITICAL": policy.critical_radius_km, "URGENT": policy.urgent_radius_km, "ROUTINE": policy.routine_radius_km}.get(str(urgency).upper(), policy.routine_radius_km)
