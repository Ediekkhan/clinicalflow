from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def unique_phone() -> str:
    return f"+23480{uuid4().int % 100_000_000:08d}"


def test_duplicate_phone_requires_explicit_family_intent() -> None:
    phone = unique_phone()
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/channels/whatsapp/intake",
            json={"customer_phone": phone, "raw_intake_text": "Fever and weakness"},
        )
        intercepted = client.post(
            "/api/v1/channels/whatsapp/intake",
            json={"customer_phone": phone, "raw_intake_text": "A child is coughing"},
        )
        continued = client.post(
            "/api/v1/channels/whatsapp/intake",
            json={"customer_phone": phone, "intent": "CONTINUE_EXISTING"},
        )
        family_ticket = client.post(
            "/api/v1/channels/whatsapp/intake",
            json={
                "customer_phone": phone,
                "raw_intake_text": "A child is coughing",
                "intent": "REGISTER_NEW_PATIENT",
            },
        )

    assert first.status_code == 200
    assert first.json()["action"] == "TICKET_CREATED"
    assert intercepted.json()["action"] == "SHOW_IDENTITY_MENU"
    assert [option["id"] for option in intercepted.json()["menu"]] == [
        "CONTINUE_EXISTING",
        "REGISTER_NEW_PATIENT",
        "BOOK_APPOINTMENT",
    ]
    assert continued.json()["active_ticket_id"] == first.json()["ticket"]["id"]
    assert family_ticket.json()["ticket"]["id"] != first.json()["ticket"]["id"]
    assert family_ticket.json()["account_group_phone"] == phone


def test_sms_duplicate_response_uses_low_bandwidth_reply_menu() -> None:
    phone = unique_phone()
    with TestClient(app) as client:
        client.post(
            "/api/v1/channels/sms/intake",
            json={"customer_phone": phone, "raw_intake_text": "Headache and nausea"},
        )
        response = client.post(
            "/api/v1/channels/sms/intake",
            json={"customer_phone": phone, "raw_intake_text": "Another patient"},
        )

    assert response.status_code == 200
    assert response.json()["action"] == "SHOW_IDENTITY_MENU"
    assert "Reply 1" in response.json()["message"]


def test_new_channel_intake_requires_a_complaint() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/channels/whatsapp/intake",
            json={"customer_phone": unique_phone()},
        )
    assert response.status_code == 422


def test_sms_can_confirm_and_cancel_a_live_database_slot() -> None:
    phone = unique_phone()
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/channels/sms/intake",
            json={"customer_phone": phone, "raw_intake_text": "Routine clinic appointment"},
        )
        assert created.status_code == 200
        menu = client.post(
            "/api/v1/channels/sms/intake",
            json={"customer_phone": phone, "intent": "BOOK_APPOINTMENT"},
        )
        assert menu.status_code == 200
        slot_id = menu.json()["menu"][0]["id"]
        confirmed = client.post(
            "/api/v1/channels/sms/intake",
            json={"customer_phone": phone, "intent": "CONFIRM_APPOINTMENT", "slot_id": slot_id},
        )
        cancelled = client.post(
            "/api/v1/channels/sms/intake",
            json={"customer_phone": phone, "intent": "CANCEL_APPOINTMENT"},
        )

    assert confirmed.status_code == 200
    assert confirmed.json()["action"] == "APPOINTMENT_BOOKED"
    assert cancelled.status_code == 200
    assert cancelled.json()["action"] == "APPOINTMENT_CANCELLED"
