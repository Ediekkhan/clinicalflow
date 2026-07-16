from fastapi.testclient import TestClient

from app.main import app


def test_notification_api_matches_existing_frontend_contract_and_persists_reads() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/patient/login", json={"phone": "+2348012345678", "password": "Password123!"})
        listed = client.get("/api/v1/notifications")
        assert listed.status_code == 200
        if listed.json():
            notification = listed.json()[0]
            marked = client.patch(f"/api/v1/notifications/{notification['id']}/read", json={})
            reloaded = client.get("/api/v1/notifications")
            assert marked.status_code == 200
            assert next(item for item in reloaded.json() if item["id"] == notification["id"])["is_read"] is True
        all_read = client.patch("/api/v1/notifications/read-all", json={})

    assert all_read.status_code == 200
