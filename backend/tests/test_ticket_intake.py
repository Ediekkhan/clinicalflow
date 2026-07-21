import re

from fastapi.testclient import TestClient

from app.main import app


def create_ticket(client: TestClient, phone: str, complaint: str = "Persistent chest pain"):
    return client.post(
        "/api/v1/tickets",
        json={"customer_phone": phone, "raw_intake_text": complaint, "channel": "WEB"},
    )


def test_ticket_intake_normalizes_phone_and_persists_complaint() -> None:
    with TestClient(app) as client:
        response = create_ticket(client, "0801 234 5678")

    assert response.status_code == 201
    payload = response.json()
    assert payload["customer_phone"] == "+2348012345678"
    assert payload["raw_intake_text"] == "Persistent chest pain"
    assert re.fullmatch(r"SV-\d{4}-\d{4}-[A-F0-9]{6}", payload["ticket_number"])


def test_patient_ticket_list_is_limited_to_account_phone() -> None:
    with TestClient(app) as client:
        own = create_ticket(client, "+2348012345678", "My own intake").json()
        other = create_ticket(client, "+2348099999999", "Another patient's intake").json()
        login = client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "Password123!"},
        )
        response = client.get("/api/v1/tickets")

    assert login.status_code == 200
    ids = {ticket["id"] for ticket in response.json()}
    assert own["id"] in ids
    assert other["id"] not in ids


def test_invalid_non_nigerian_phone_is_rejected() -> None:
    with TestClient(app) as client:
        response = create_ticket(client, "+15551234567")
    assert response.status_code == 422
