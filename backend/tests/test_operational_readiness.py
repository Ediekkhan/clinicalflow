import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app


def test_unsafe_production_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Unsafe production configuration"):
        Settings(app_environment="production", database_url="sqlite+aiosqlite:///unsafe.db", auto_create_schema=True, auth_cookie_secure=False, channel_webhook_secret="change-me")


def test_request_id_metrics_and_retention_job_are_operational() -> None:
    with TestClient(app) as client:
        health = client.get("/health", headers={"x-request-id": "readiness-test"})
        metrics = client.get("/metrics")
        client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        retention = client.post("/api/v1/admin/maintenance/retention")

    assert health.headers["x-request-id"] == "readiness-test"
    assert "synaptiverse_requests_total" in metrics.text
    assert retention.status_code == 200
    assert {"sessions_deleted", "audit_logs_deleted", "demo_leads_deleted"} <= retention.json().keys()
