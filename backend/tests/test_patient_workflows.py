from fastapi.testclient import TestClient

from app.main import app


def test_patient_profile_card_history_and_dashboard_are_persistent() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/patient/login", json={"phone": "+2348012345678", "password": "Password123!"})
        profile = client.patch(
            "/api/v1/patient/profile",
            json={"full_name": "Ada Okafor", "emergency_contact": "+2348099999999", "hmo_provider": "Demo HMO", "current_medications": "None"},
        )
        card = client.patch("/api/v1/patient/card-details", json={"blood_group": "O+", "genotype": "AA", "known_allergies": "Penicillin"})
        ticket = client.post("/api/v1/tickets", json={"customer_phone": "+2348012345678", "raw_intake_text": "Persistent headache", "channel": "WEB"})
        history = client.get("/api/v1/patient/history")
        dashboard = client.get("/api/v1/patient/dashboard")
        reloaded = client.get("/api/v1/auth/patient/me")

    assert login.status_code == 200
    assert profile.status_code == 200
    assert card.status_code == 200
    assert ticket.status_code == 201
    assert any(event["id"] == ticket.json()["id"] for event in history.json())
    assert dashboard.status_code == 200
    assert dashboard.json()["stats"]["active_tickets"] >= 1
    assert reloaded.json()["blood_group"] == "O+"
    assert reloaded.json()["known_allergies"] == "Penicillin"
    assert reloaded.json()["emergency_contact"] == "+2348099999999"


def test_non_patient_cannot_update_patient_card() -> None:
    with TestClient(app) as client:
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        response = client.patch("/api/v1/patient/card-details", json={"blood_group": "A+"})

    assert response.status_code == 403
