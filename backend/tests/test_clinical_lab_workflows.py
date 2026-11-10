import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuthAccount, ConsentRecord, SignupApplication, StaffMembership, Tenant
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, create_session, hash_password

PASSWORD = "Password123!"


async def seed_workflow():
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    async with app.state.session_factory() as session:
        origin = Tenant(name=f"Origin {suffix}", state_location="Origin", status="ACTIVE", accepts_patients=True)
        destination = Tenant(name=f"Destination {suffix}", state_location="Destination", status="ACTIVE", accepts_patients=True)
        laboratory = Tenant(name=f"Laboratory {suffix}", state_location="Laboratory", status="ACTIVE", accepts_patients=False)
        unrelated = Tenant(name=f"Unrelated {suffix}", state_location="Unrelated", status="ACTIVE", accepts_patients=True)
        session.add_all([origin, destination, laboratory, unrelated]); await session.flush()
        patient = AuthAccount(tenant_id=origin.id, role="patient", identifier=f"patient-{suffix}", password_hash=hash_password(PASSWORD), first_name="Patient", last_name="Person", is_active=True)
        doctor = AuthAccount(tenant_id=origin.id, role="doctor", identifier=f"doctor-{suffix}", password_hash=hash_password(PASSWORD), first_name="Ordering", last_name="Doctor", is_active=True)
        destination_admin = AuthAccount(tenant_id=destination.id, role="hospital_admin", identifier=f"destination-{suffix}", password_hash=hash_password(PASSWORD), first_name="Destination", last_name="Admin", is_active=True)
        lab_admin = AuthAccount(tenant_id=laboratory.id, role="admin", identifier=f"lab-{suffix}", password_hash=hash_password(PASSWORD), first_name="Lab", last_name="Admin", is_active=True)
        unrelated_admin = AuthAccount(tenant_id=unrelated.id, role="hospital_admin", identifier=f"unrelated-{suffix}", password_hash=hash_password(PASSWORD), first_name="Unrelated", last_name="Admin", is_active=True)
        session.add_all([patient, doctor, destination_admin, lab_admin, unrelated_admin]); await session.flush()
        session.add_all([
            StaffMembership(user_id=doctor.id, hospital_id=origin.id, department_id="General Medicine", role="doctor", specialty_id="General Medicine", professional_license_number=f"LIC-{suffix}", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1)),
            StaffMembership(user_id=destination_admin.id, hospital_id=destination.id, department_id="Administration", role="hospital_admin", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1)),
            StaffMembership(user_id=unrelated_admin.id, hospital_id=unrelated.id, department_id="Administration", role="hospital_admin", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1)),
        ])
        application = SignupApplication(reference=f"CONSENT-{suffix}", application_type="patient", onboarding_type="PUBLIC_SELF_REGISTRATION", status="APPROVED", country="NG", payload_json="{}", consent_version="1")
        session.add(application); await session.flush(); session.add(ConsentRecord(signup_application_id=application.id, account_id=patient.id, consent_type="CARE_DATA_SHARING", policy_version="1", accepted=True))
        tokens = {name: await create_session(session, account) for name, account in {"patient": patient, "doctor": doctor, "destination": destination_admin, "lab": lab_admin, "unrelated": unrelated_admin}.items()}
        await session.commit()
        return {"origin": origin.id, "destination": destination.id, "laboratory": laboratory.id, "patient": patient.id, "doctor": doctor.id, "tokens": tokens}


def use_session(client, issued):
    client.cookies.set(ACCESS_COOKIE, issued.access_token)
    client.cookies.set(REFRESH_COOKIE, issued.refresh_token)


def test_referral_destination_decision_transfer_and_encounter_isolation():
    with TestClient(app) as client:
        case = asyncio.run(seed_workflow()); use_session(client, case["tokens"]["doctor"])
        created = client.post("/api/v1/referrals", json={"patient_id": str(case["patient"]), "destination_facility_id": str(case["destination"]), "required_capability": "Cardiac monitoring", "required_specialty": "Cardiology", "clinical_summary": "Authorized referral summary"})
        assert created.status_code == 201, created.text
        referral_id = created.json()["id"]
        use_session(client, case["tokens"]["unrelated"])
        assert client.patch(f"/api/v1/referrals/{referral_id}/decision", json={"decision": "ACCEPTED"}).status_code == 404
        use_session(client, case["tokens"]["destination"])
        accepted = client.patch(f"/api/v1/referrals/{referral_id}/decision", json={"decision": "ACCEPTED"})
        assert accepted.status_code == 200 and accepted.json()["status"] == "ACCEPTED"
        use_session(client, case["tokens"]["doctor"])
        transfer = client.post(f"/api/v1/referrals/{referral_id}/transfer", json={"transport_mode": "AMBULANCE", "handoff_notes": "Stable for transfer"})
        assert transfer.status_code == 201
        assert client.post(f"/api/v1/referrals/{referral_id}/encounters").status_code == 404
        use_session(client, case["tokens"]["destination"])
        teleconsult = client.post(f"/api/v1/referrals/{referral_id}/teleconsultation", json={"specialist_id": str(case["doctor"]), "duration_hours": 4, "regulatory_approval_confirmed": True})
        assert teleconsult.status_code == 201, teleconsult.text
        use_session(client, case["tokens"]["patient"])
        withdrawn = client.post(f"/api/v1/referrals/{referral_id}/withdraw-consent")
        assert withdrawn.status_code == 200 and withdrawn.json()["status"] == "CONSENT_WITHDRAWN"
        use_session(client, case["tokens"]["destination"])
        assert client.post(f"/api/v1/referrals/{referral_id}/teleconsultation", json={"specialist_id": str(case["doctor"]), "regulatory_approval_confirmed": True}).status_code == 404


def test_laboratory_chain_critical_acknowledgement_and_release_policy():
    with TestClient(app) as client:
        case = asyncio.run(seed_workflow()); use_session(client, case["tokens"]["doctor"])
        order_response = client.post("/api/v1/laboratory/orders", json={"patient_id": str(case["patient"]), "laboratory_id": str(case["laboratory"]), "priority": "URGENT", "tests": [{"test_code": "TEST-A", "display": "Requested assay", "loinc_code": "1234-5", "specimen_type": "Blood"}]})
        assert order_response.status_code == 201, order_response.text
        order = order_response.json(); test_id = order["tests"][0]["id"]
        use_session(client, case["tokens"]["destination"])
        assert client.post(f"/api/v1/laboratory/orders/{order['id']}/accept").status_code == 403
        use_session(client, case["tokens"]["lab"])
        assert client.post(f"/api/v1/laboratory/orders/{order['id']}/accept").status_code == 200
        specimen = client.post(f"/api/v1/laboratory/orders/{order['id']}/specimens", json={"specimen_type": "Blood", "collection_site": "Laboratory"})
        assert specimen.status_code == 201
        assert client.patch(f"/api/v1/laboratory/specimens/{specimen.json()['id']}/status", json={"status": "RECEIVED", "location": "Processing bench"}).status_code == 200
        result = client.post(f"/api/v1/laboratory/orders/{order['id']}/results", json={"ordered_test_id": test_id, "value": "Critical value", "is_critical": True, "status": "PRELIMINARY"})
        assert result.status_code == 201
        corrected = client.post(f"/api/v1/laboratory/results/{result.json()['id']}/correct", json={"corrected_value": "Confirmed critical value", "reason": "Quality control repeat confirmed correction"})
        assert corrected.status_code == 200 and corrected.json()["status"] == "CORRECTED"
        finalized = client.post(f"/api/v1/laboratory/orders/{order['id']}/finalize", json={"decision": "APPROVED", "conclusion": "Reviewed final report"})
        assert finalized.status_code == 200
        assert client.post(f"/api/v1/laboratory/orders/{order['id']}/release").status_code == 409
        use_session(client, case["tokens"]["unrelated"])
        assert client.post(f"/api/v1/laboratory/results/{result.json()['id']}/acknowledge", json={}).status_code in {403, 404}
        use_session(client, case["tokens"]["doctor"])
        assert client.post(f"/api/v1/laboratory/results/{result.json()['id']}/acknowledge", json={"action_taken": "Patient contacted"}).status_code == 200
        use_session(client, case["tokens"]["lab"])
        assert client.post(f"/api/v1/laboratory/orders/{order['id']}/release").status_code == 200
        use_session(client, case["tokens"]["patient"])
        results = client.get("/api/v1/patients/me/laboratory-results")
        assert results.status_code == 200 and len(results.json()) == 1
