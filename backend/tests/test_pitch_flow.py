from fastapi.testclient import TestClient

from app.main import app


def test_pitch_booking_to_waiting_room_and_patient_tracking_flow() -> None:
    with TestClient(app) as client:
        booking = client.post(
            "/api/v1/tickets",
            json={
                "customer_phone": "+2348012345678",
                "raw_intake_text": "Chest pain and dizziness",
                "channel": "WEB",
            },
        )
        assert booking.status_code == 201
        ticket = booking.json()

        nurse_login = client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        assert nurse_login.status_code == 200
        queue = client.get("/api/v1/tickets")
        assert ticket["id"] in {row["id"] for row in queue.json()}

        escalated = client.patch(f"/api/v1/tickets/{ticket['id']}/escalate")
        assert escalated.json()["urgency_level"] == "CRITICAL"
        started = client.patch(f"/api/v1/tickets/{ticket['id']}", json={"queue_status": "BEING_SEEN"})
        assert started.json()["queue_status"] == "BEING_SEEN"

        waiting_room = client.get("/api/v1/hospital/waiting-room")
        assert waiting_room.json()["now_serving"]["ticket_number"] == ticket["ticket_number"]

        patient_login = client.post(
            "/api/v1/auth/patient/login",
            json={"phone": "+2348012345678", "password": "Password123!"},
        )
        assert patient_login.status_code == 200
        patient_tickets = client.get("/api/v1/tickets")
        assert ticket["id"] in {row["id"] for row in patient_tickets.json()}
        patient_queue = client.get("/api/v1/patient/queue")
        assert patient_queue.json()["queue_status"] == "BEING_SEEN"
