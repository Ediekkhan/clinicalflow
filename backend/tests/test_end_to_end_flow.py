import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.models import Tenant, AuthAccount, StaffMembership, Provider, ProviderSlot
from app.services.auth_service import hash_password
from app.models import UTC


def seed_hospital_and_doctor(specialty: str):
    async def _seed():
        async with app.state.session_factory() as session:
            tenant = await session.get(Tenant, UUID(settings.default_tenant_id))
            if tenant is None:
                tenant = Tenant(id=UUID(settings.default_tenant_id), name="ClinicalFlow", state_location="TestState", latitude=6.5, longitude=3.3, accepts_patients=True, status="ACTIVE")
                session.add(tenant)
                await session.flush()
            doctor = AuthAccount(
                tenant_id=tenant.id,
                role="specialist",
                identifier=f"doc-{uuid4().hex[:6]}",
                password_hash=hash_password("DocPass1"),
                first_name="Doc",
                last_name="Tester",
                phone=f"+1555{int(uuid4().hex[:8],16)%100000000:08d}",
                email=f"doc{uuid4().hex[:6]}@example.org",
                specialty=specialty,
                is_active=True,
            )
            session.add(doctor)
            await session.flush()
            membership = StaffMembership(user_id=doctor.id, hospital_id=tenant.id, department_id=specialty, role="specialist", specialty_id=specialty, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True)
            session.add(membership)
            await session.flush()
            provider = Provider(tenant_id=tenant.id, full_name=f"Dr. {doctor.first_name} {doctor.last_name}", specialty=specialty, doctor_id=doctor.id, room_label="A1", is_active=True)
            session.add(provider)
            await session.flush()
            starts = __import__('datetime').datetime.now(UTC) + timedelta(hours=1)
            slot = ProviderSlot(tenant_id=tenant.id, provider_id=provider.id, starts_at=starts, ends_at=starts + timedelta(minutes=30), is_locked=False, is_booked=False)
            session.add(slot)
            await session.commit()
            return str(tenant.id), str(doctor.id), str(slot.id), doctor.email
    return asyncio.run(_seed())


def test_end_to_end_patient_journey(monkeypatch):
    # Fix OTP generation to a known code
    monkeypatch.setattr("app.routes.secrets.randbelow", lambda n: 123456)

    patient_phone = f"+23480{uuid4().int % 100_000_000:08d}"
    payload = {
        "first_name": "New",
        "last_name": "Patient",
        "phone": patient_phone,
        "email": None,
        "country": "TestLand",
        "region": "TestRegion",
        "password": "PatientPass1",
        "confirm_password": "PatientPass1",
        "accept_terms": True,
        "accept_privacy": True,
        "marketing_consent": False,
        "data": {"date_of_birth": "1990-01-01", "city": "TestCity", "emergency_contact_phone": "+14150000000"},
    }

    with TestClient(app, base_url="https://testserver") as client:
        symptom_text = "fever and cough"
        clinical_route = asyncio.run(app.state.knowledge_graph.route(symptom_text))
        tenant_id, doctor_id, slot_id, doctor_email = seed_hospital_and_doctor(clinical_route.target_specialty)

        # signup
        r = client.post("/api/v1/signup/patient", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "PHONE_VERIFICATION_REQUIRED"
        application_id = body["id"]

        # verify (OTP will be 123456 due to monkeypatch), endpoint will also set session cookies
        verify_resp = client.post("/api/v1/signup/verify-phone", json={"application_id": application_id, "code": "123456"})
        assert verify_resp.status_code == 200, verify_resp.text
        vbody = verify_resp.json()
        assert vbody["status"] == "ACTIVE"
        # ensure the verify endpoint attempted to create session cookies by accessing the profile
        me = client.get("/api/v1/auth/patient/me")
        assert me.status_code == 200, me.text

        # create a ticket (triage)
        ticket_payload = {"customer_phone": patient_phone, "raw_intake_text": symptom_text, "channel": "WEB"}
        ticket_resp = client.post("/api/v1/tickets", json=ticket_payload)
        assert ticket_resp.status_code == 201, ticket_resp.text
        ticket = ticket_resp.json()
        ticket_id = ticket["id"] if isinstance(ticket, list) else ticket.get("id")
        # ensure ticket exists
        assert ticket_id is not None

        # book an appointment using seeded slot_id
        appt_payload = {"ticket_id": ticket_id, "slot_id": slot_id, "customer_phone": patient_phone}
        appt_resp = client.post("/api/v1/appointments", json=appt_payload)
        # booking may succeed or raise if something mismatches — assert success
        assert appt_resp.status_code == 201, appt_resp.text
        appt = appt_resp.json()
        assert appt.get("status") in {"BOOKED", "AWAITING_CLINICAL_REVIEW", "SPECIALIST_UNAVAILABLE"}

    # Doctor logs in and creates consultation note
    with TestClient(app, base_url="https://testserver") as doctor_client:
        login_payload = {"email": doctor_email, "password": "DocPass1"}
        login = doctor_client.post("/api/v1/auth/specialist/login", json=login_payload)
        assert login.status_code == 200, login.text
        # create note as the specialist
        note_resp = doctor_client.post(f"/api/v1/specialist/patients/{ticket_id}/notes", json={"body": "Consultation completed: patient advised."})
        assert note_resp.status_code == 201, note_resp.text
        note = note_resp.json()
        assert note.get("id") is not None
