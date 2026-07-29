"""Dedicated newly-registered patient to completed consultation journey."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuthAccount, StaffMembership
from app.services.auth_service import create_session, hash_password
from test_doctor_assignment import PASSWORD, PHONE, seed_case, use_session


def test_new_patient_hospital_acceptance_nurse_assessment_and_doctor_consultation() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())

        async def add_journey_accounts() -> dict:
            async with app.state.session_factory() as session:
                now = datetime.now(UTC)
                patient = AuthAccount(
                    tenant_id=fixture["hospital"], role="patient", identifier=f"journey-{uuid4().hex}@example.org",
                    password_hash=hash_password(PASSWORD), first_name="Journey", last_name="Patient",
                    phone=PHONE, is_active=True,
                )
                admin = AuthAccount(
                    tenant_id=fixture["hospital"], role="hospital_admin", identifier=f"journey-admin-{uuid4().hex}",
                    password_hash=hash_password(PASSWORD), first_name="Hospital", last_name="Coordinator", is_active=True,
                )
                nurse = AuthAccount(
                    tenant_id=fixture["hospital"], role="nurse", identifier=f"journey-nurse-{uuid4().hex}",
                    password_hash=hash_password(PASSWORD), first_name="Care", last_name="Nurse", is_active=True,
                )
                session.add_all([patient, admin, nurse])
                await session.flush()
                session.add_all([
                    StaffMembership(user_id=admin.id, hospital_id=fixture["hospital"], department_id="Administration", role="hospital_admin", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1)),
                    StaffMembership(user_id=nurse.id, hospital_id=fixture["hospital"], department_id=fixture["specialty"], role="nurse", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1)),
                ])
                await session.flush()
                tokens = {name: await create_session(session, account) for name, account in {"patient": patient, "admin": admin, "nurse": nurse}.items()}
                await session.commit()
                return {"patient": patient, "tokens": tokens}

        journey = asyncio.run(add_journey_accounts())
        patient = journey["patient"]

        # The facility accepts the routed ticket before clinical work begins.
        use_session(client, journey["tokens"]["admin"])
        accepted = client.post(f"/api/v1/hospital/tickets/{fixture['ticket']}/facility-decision", json={"decision": "ACCEPT"})
        assert accepted.status_code == 201, accepted.text

        # The newly registered patient books into the routed hospital's eligible doctor slot.
        use_session(client, journey["tokens"]["patient"])
        booked = client.post("/api/v1/appointments", json={"ticket_id": str(fixture["ticket"]), "slot_id": str(fixture["slot"]), "customer_phone": patient.phone})
        assert booked.status_code == 201, booked.text
        appointment = booked.json()
        assert appointment["hospital_id"] == str(fixture["hospital"])
        assert appointment["doctor_id"] == str(fixture["doctor"])

        # The nurse records a real observation through the supported offline-capable API.
        use_session(client, journey["tokens"]["nurse"])
        queued = client.post("/api/v1/offline/mutations", json={
            "client_mutation_id": f"journey-{uuid4().hex}", "mutation_type": "OBSERVATION",
            "payload": {"patient_id": str(patient.id), "code": "heart-rate", "display": "Heart rate", "value": "78", "unit": "bpm"},
        })
        assert queued.status_code == 202, queued.text
        synced = client.post("/api/v1/offline/mutations/sync")
        assert synced.status_code == 200 and synced.json()["synced"] == 1, synced.text

        # Only the assigned doctor can open the consultation and author its note.
        use_session(client, fixture["doctor_tokens"])
        encounter = client.post(f"/api/v1/appointments/{appointment['id']}/encounter")
        assert encounter.status_code == 201, encounter.text
        note = client.post(f"/api/v1/encounters/{encounter.json()['id']}/notes", json={"body": "Consultation completed after nurse assessment."})
        assert note.status_code == 201, note.text

        use_session(client, journey["tokens"]["patient"])
        history = client.get("/api/v1/patient/history")
        assert history.status_code == 200
        assert any(item["type"] == "APPOINTMENT" and item["id"] == appointment["id"] for item in history.json())
