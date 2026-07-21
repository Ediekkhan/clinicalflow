from fastapi.testclient import TestClient

from app.main import app


PHONE = "+2348012345678"


def create_ticket(client: TestClient, complaint: str) -> dict:
    response = client.post("/api/v1/tickets", json={"customer_phone": PHONE, "raw_intake_text": complaint, "channel": "WEB"})
    assert response.status_code == 201
    return response.json()


def available_slots(client: TestClient) -> list[dict]:
    response = client.get("/api/v1/appointments/slots")
    assert response.status_code == 200
    return [slot for slot in response.json() if not slot["is_locked"] and not slot["is_booked"]]


def test_appointment_booking_reschedule_and_cancel_lifecycle() -> None:
    with TestClient(app) as client:
        first_slot, second_slot = available_slots(client)[:2]
        ticket = create_ticket(client, "Scheduling lifecycle test")
        booked = client.post(
            "/api/v1/appointments",
            json={"ticket_id": ticket["id"], "slot_id": first_slot["id"], "customer_phone": PHONE},
        )
        assert booked.status_code == 201
        appointment = booked.json()
        assert appointment["status"] == "BOOKED"

        client.post("/api/v1/auth/patient/login", json={"phone": PHONE, "password": "Password123!"})
        moved = client.patch(f"/api/v1/appointments/{appointment['id']}/reschedule", json={"slot_id": second_slot["id"]})
        assert moved.status_code == 200
        assert moved.json()["slot_id"] == second_slot["id"]

        cancelled = client.patch(f"/api/v1/appointments/{appointment['id']}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"
        refreshed = {slot["id"]: slot for slot in client.get("/api/v1/appointments/slots").json()}
        assert refreshed[first_slot["id"]]["is_booked"] is False
        assert refreshed[second_slot["id"]]["is_booked"] is False


def test_slot_cannot_be_double_booked() -> None:
    with TestClient(app) as client:
        slot = available_slots(client)[0]
        first_ticket = create_ticket(client, "First booking")
        second_ticket = create_ticket(client, "Second booking")
        first = client.post("/api/v1/appointments", json={"ticket_id": first_ticket["id"], "slot_id": slot["id"], "customer_phone": PHONE})
        second = client.post("/api/v1/appointments", json={"ticket_id": second_ticket["id"], "slot_id": slot["id"], "customer_phone": PHONE})
    assert first.status_code == 201
    assert second.status_code == 409


def test_staff_emergency_block_prevents_booking() -> None:
    with TestClient(app) as client:
        slot = available_slots(client)[0]
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        locked = client.patch(f"/api/v1/appointments/slots/{slot['id']}/lock", json={"is_locked": True, "reason": "Emergency theatre demand"})
        assert locked.status_code == 200
        client.post("/api/v1/auth/logout")
        ticket = create_ticket(client, "Blocked slot test")
        booking = client.post("/api/v1/appointments", json={"ticket_id": ticket["id"], "slot_id": slot["id"], "customer_phone": PHONE})
        assert booking.status_code == 409

        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        unlocked = client.patch(f"/api/v1/appointments/slots/{slot['id']}/lock", json={"is_locked": False})
    assert unlocked.status_code == 200
