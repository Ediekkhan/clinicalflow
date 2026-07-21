from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_ticket_mutations_are_idempotent_and_version_checked() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/tickets",
            json={"customer_phone": "+2348012345678", "raw_intake_text": "Offline mutation test", "channel": "WEB"},
        ).json()
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        key = str(uuid4())
        first = client.patch(
            f"/api/v1/tickets/{created['id']}",
            json={"queue_status": "BEING_SEEN", "expected_version": created["version"]},
            headers={"x-idempotency-key": key},
        )
        replay = client.patch(
            f"/api/v1/tickets/{created['id']}",
            json={"queue_status": "BEING_SEEN", "expected_version": created["version"]},
            headers={"x-idempotency-key": key},
        )
        stale = client.patch(
            f"/api/v1/tickets/{created['id']}",
            json={"queue_status": "RESOLVED", "expected_version": created["version"]},
            headers={"x-idempotency-key": str(uuid4())},
        )

    assert first.status_code == 200
    assert first.json()["version"] == created["version"] + 1
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert stale.status_code == 409
    assert stale.json()["detail"]["current"]["version"] == first.json()["version"]


def test_idempotency_key_cannot_be_reused_for_another_action() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/tickets",
            json={"customer_phone": "+2348012345678", "raw_intake_text": "Key reuse test", "channel": "WEB"},
        ).json()
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        key = str(uuid4())
        client.patch(
            f"/api/v1/tickets/{created['id']}",
            json={"queue_status": "BEING_SEEN", "expected_version": created["version"]},
            headers={"x-idempotency-key": key},
        )
        response = client.patch(
            f"/api/v1/tickets/{created['id']}/escalate",
            headers={"x-idempotency-key": key, "x-expected-version": str(created["version"] + 1)},
        )
    assert response.status_code == 409
