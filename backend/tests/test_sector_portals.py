from fastapi.testclient import TestClient

from app.main import app


SECTOR_RESOURCES = {
    "pharmacy": ("dashboard", "analytics", "deliveries", "inventory", "notifications", "patients", "prescriptions", "settings"),
    "lab": ("dashboard", "analytics", "collections", "equipment", "notifications", "patients", "requests", "results", "settings"),
    "hmo": ("dashboard", "analytics", "authorizations", "claims", "facilities", "members", "notifications", "patients", "payments", "settings", "utilization"),
    "moh": ("dashboard", "facilities", "reports", "settings", "surveillance"),
    "admin": ("dashboard", "facilities", "messages", "people", "settings", "vitals"),
}


def test_admin_can_load_every_sector_portal_contract() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        responses = {
            f"{entity}/{resource}": client.get(f"/api/v1/{entity}/{resource}")
            for entity, resources in SECTOR_RESOURCES.items()
            for resource in resources
        }

    assert login.status_code == 200
    failures = {path: response.status_code for path, response in responses.items() if response.status_code != 200}
    assert failures == {}
    assert responses["admin/people"].json()["items"]
    assert responses["moh/facilities"].json()["items"]
    assert len(responses["admin/vitals"].json()["items"]) == 3


def test_patient_cannot_access_sector_portal_data() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/patient/login", json={"phone": "+2348012345678", "password": "Password123!"})
        responses = [client.get("/api/v1/pharmacy/dashboard"), client.get("/api/v1/admin/people")]

    assert [response.status_code for response in responses] == [403, 403]


def test_admin_can_create_and_update_sector_records() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        created = client.post("/api/v1/pharmacy/inventory", json={"title": "Oral rehydration salts", "description": "24 sachets", "status": "LOW_STOCK"})
        updated = client.patch(f"/api/v1/pharmacy/inventory/{created.json()['id']}", json={"description": "100 sachets", "status": "ACTIVE"})
        inventory = client.get("/api/v1/pharmacy/inventory")

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["status"] == "ACTIVE"
    assert any(item["id"] == created.json()["id"] and item["description"] == "100 sachets" for item in inventory.json()["items"])
