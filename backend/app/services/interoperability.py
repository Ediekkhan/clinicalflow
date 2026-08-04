from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


class IntegrationNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class InteroperabilityAdapter:
    name: str
    base_url: str | None = None
    api_key: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def require_configured(self) -> None:
        if not self.configured:
            raise IntegrationNotConfigured(f"{self.name} integration is not configured")


def fhir_resource(resource_type: str, resource_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"resourceType": resource_type, "id": resource_id, **fields}


def terminology_manifest(*, source: str, version: str, license_reference: str | None, checksum: str, reviewed_by: str | None) -> dict[str, Any]:
    if not source.strip() or not version.strip() or not checksum.strip():
        raise ValueError("Terminology source, version, and checksum are required")
    if not license_reference or not reviewed_by:
        raise ValueError("Licensed terminology requires a license reference and reviewer")
    return {"source": source, "version": version, "license_reference": license_reference, "checksum": checksum, "reviewed_by": reviewed_by}


def verify_checksum(content: bytes, expected: str) -> bool:
    return hashlib.sha256(content).hexdigest().lower() == expected.strip().lower()
