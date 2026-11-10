from fastapi.testclient import TestClient

from app.main import app


def test_nurse_clinic_and_hospital_operational_resources_are_live() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        responses = {
            path: client.get(path)
            for path in (
                "/api/v1/nurse/dashboard",
                "/api/v1/nurse/patients",
                "/api/v1/nurse/schedule",
                "/api/v1/clinic/dashboard",
                "/api/v1/clinic/doctors",
                "/api/v1/clinic/notifications",
                "/api/v1/hospital/dashboard",
                "/api/v1/hospital/departments",
                "/api/v1/hospital/settings",
            )
        }

    assert login.status_code == 200
    assert all(response.status_code == 200 for response in responses.values())
    assert len(responses["/api/v1/nurse/dashboard"].json()["stats"]) == 4
    assert responses["/api/v1/clinic/doctors"].json()["items"]
    assert responses["/api/v1/hospital/settings"].json()["facility_name"] == "ClinicalFlow Demo Clinic"


def test_patient_cannot_access_operational_staff_portals() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/patient/login", json={"phone": "+2348012345678", "password": "Password123!"})
        response = client.get("/api/v1/hospital/dashboard")

    assert response.status_code == 403
