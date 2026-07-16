from fastapi.testclient import TestClient

from app.main import app


def test_specialist_assignment_status_notes_messages_and_surfaces() -> None:
    with TestClient(app) as client:
        ticket = client.post("/api/v1/tickets", json={"customer_phone": "+2348088888888", "raw_intake_text": "Fever and cough", "channel": "WEB"}).json()
        login = client.post("/api/v1/auth/specialist/login", json={"email": "dr.ada@example.com", "password": "Password123!"})
        assignment = client.patch(f"/api/v1/specialist/patients/{ticket['id']}/assign-self")
        status = client.patch(f"/api/v1/specialist/patients/{ticket['id']}/status", json={"queue_status": "BEING_SEEN"})
        note = client.post(f"/api/v1/specialist/patients/{ticket['id']}/notes", json={"body": "Reviewed symptoms and advised hydration."})
        message = client.post("/api/v1/specialist/messages", json={"sender_label": "Dr. Ada", "body": "Patient review completed."})
        surfaces = {resource: client.get(f"/api/v1/specialist/{resource}") for resource in ("dashboard", "queue", "appointments", "schedule", "notes", "messages", "earnings", "notifications", "settings")}

    assert login.status_code == 200
    assert assignment.status_code == 200
    assert status.json()["queue_status"] == "BEING_SEEN"
    assert note.status_code == 201
    assert message.status_code == 201
    assert all(response.status_code == 200 for response in surfaces.values())
    assert any(item["id"] == ticket["id"] and item["status"] == "ASSIGNED" for item in surfaces["queue"].json()["items"])
    assert surfaces["notes"].json()["items"][0]["status"] == "SIGNED"
    assert surfaces["messages"].json()["items"][0]["status"] == "READ"


def test_specialist_cannot_update_unassigned_ticket_status() -> None:
    with TestClient(app) as client:
        ticket = client.post("/api/v1/tickets", json={"customer_phone": "+2348077777777", "raw_intake_text": "Routine headache", "channel": "WEB"}).json()
        client.post("/api/v1/auth/specialist/login", json={"email": "dr.ada@example.com", "password": "Password123!"})
        response = client.patch(f"/api/v1/specialist/patients/{ticket['id']}/status", json={"queue_status": "RESOLVED"})

    assert response.status_code == 404
