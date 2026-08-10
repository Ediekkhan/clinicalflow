from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TextDirection = Literal["ltr", "rtl"]
MeasurementSystem = Literal["metric", "imperial", "mixed"]
DataResidencyScope = Literal["region_scoped", "country_scoped"]


class RegionPolicyProfile(BaseModel):
    region_id: str = Field(min_length=2, max_length=64)
    country_code: str = Field(min_length=2, max_length=3)
    display_name: str = Field(min_length=2, max_length=128)
    default_language: str = Field(min_length=2, max_length=16)
    supported_languages: list[str] = Field(default_factory=lambda: ["en"])
    text_direction: TextDirection = "ltr"
    time_zones: list[str] = Field(default_factory=lambda: ["UTC"])
    currency_code: str = Field(min_length=3, max_length=3)
    measurement_system: MeasurementSystem = "metric"
    emergency_guidance_source: Literal["verified_regional_configuration"] = "verified_regional_configuration"
    emergency_contact_configured: bool = False
    sensitive_data_residency: DataResidencyScope = "region_scoped"
    cross_border_transfer_requires_approval: bool = True
    clinician_jurisdiction_required: bool = True
    consent_policy_summary: str | None = Field(default=None, max_length=2000)
    retention_policy_summary: str | None = Field(default=None, max_length=2000)


class RoutingPolicy(BaseModel):
    policy_id: str = Field(min_length=2, max_length=64)
    region_id: str = Field(min_length=2, max_length=64)
    enabled_factors: list[
        Literal[
            "clinical_capability",
            "urgency",
            "travel_time",
            "capacity",
            "operating_status",
            "specialist_availability",
            "payer_coverage",
            "jurisdiction",
        ]
    ]
    requires_clinician_review: bool = True
    thresholds_are_clinician_approved: bool = False


class ClinicalSafetyBoundary(BaseModel):
    positioning: str = "Right care. Right facility. Right time."
    disclaimer: str = (
        "ClinicalFlow supports care coordination and does not diagnose, replace a clinician, "
        "or replace emergency services."
    )
    never_hardcode_emergency_contacts: bool = True
    never_encode_phi_in_qr_codes: bool = True
    cross_border_access_requires_policy_check: bool = True
    triage_requires_clinical_validation_label: bool = True


DEMO_REGION_POLICY_PROFILE = RegionPolicyProfile(
    region_id="demo-global",
    country_code="XX",
    display_name="Global Demo Region",
    default_language="en",
    supported_languages=["en", "qps-demo"],
    currency_code="USD",
)


GLOBAL_CLINICAL_SAFETY_BOUNDARY = ClinicalSafetyBoundary()
