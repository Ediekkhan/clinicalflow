from fastapi.testclient import TestClient

from app.main import app


ADMIN_RESOURCES = ("dashboard", "facilities", "messages", "people", "settings", "vitals")


def test_platform_admin_is_limited_to_platform_portal_contracts() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        responses = {resource: client.get(f"/api/v1/admin/{resource}") for resource in ADMIN_RESOURCES}
        isolated = [
            client.get("/api/v1/pharmacy/dashboard"),
            client.get("/api/v1/hmo/dashboard"),
            client.get("/api/v1/moh/dashboard"),
        ]

    assert login.status_code == 200
    assert {path: response.status_code for path, response in responses.items() if response.status_code != 200} == {}
    assert responses["people"].json()["items"]
    assert len(responses["vitals"].json()["items"]) == 3
    assert [response.status_code for response in isolated] == [403, 403, 403]


def test_patient_cannot_access_sector_portal_data() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/patient/login", json={"phone": "+2348012345678", "password": "Password123!"})
        responses = [client.get("/api/v1/pharmacy/dashboard"), client.get("/api/v1/admin/people")]

    assert [response.status_code for response in responses] == [403, 403]


def test_legacy_generic_sector_writes_are_rejected() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/staff/pin-login", json={"role": "admin", "pin": "1357"})
        created = client.post("/api/v1/pharmacy/inventory", json={"title": "Legacy inventory", "description": "Generic record", "status": "LOW_STOCK"})
        updated = client.patch(f"/api/v1/pharmacy/inventory/{'0' * 32}", json={"description": "Generic update", "status": "ACTIVE"})

    assert created.status_code == 403
    assert updated.status_code == 404