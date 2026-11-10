import pytest

from app.services.interoperability import IntegrationNotConfigured, InteroperabilityAdapter, fhir_resource, terminology_manifest


def test_fhir_resource_is_explicit_and_minimal() -> None:
    resource = fhir_resource("Patient", "patient-1", {"active": True})
    assert resource == {"resourceType": "Patient", "id": "patient-1", "active": True}


def test_external_adapter_fails_closed_without_credentials() -> None:
    with pytest.raises(IntegrationNotConfigured):
        InteroperabilityAdapter("DHIS2").require_configured()


def test_licensed_terminology_requires_provenance() -> None:
    with pytest.raises(ValueError):
        terminology_manifest(source="ICD-11", version="2026", license_reference=None, checksum="abc", reviewed_by=None)
