from fastapi.testclient import TestClient

from app.main import app


def test_admin_can_pause_and_resume_public_intake() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        paused = client.patch("/api/v1/hospital/settings", json={"intake_paused": True, "whatsapp_enabled": False})
        blocked = client.post("/api/v1/tickets", json={"customer_phone": "+2348055555555", "raw_intake_text": "Routine headache", "channel": "WEB"})
        resumed = client.patch("/api/v1/hospital/settings", json={"intake_paused": False, "whatsapp_enabled": True})

    assert login.status_code == 200
    assert paused.json()["intake_paused"] is True
    assert paused.json()["whatsapp_enabled"] is False
    assert blocked.status_code == 503
    assert resumed.json()["intake_paused"] is False


def test_non_admin_cannot_change_tenant_controls() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        response = client.patch("/api/v1/hospital/settings", json={"intake_paused": True})
    assert response.status_code == 403
