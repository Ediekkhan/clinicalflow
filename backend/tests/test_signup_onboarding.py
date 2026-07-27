import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import StaffInvitation
from app.services.auth_service import token_hash


def common_payload(suffix: str) -> dict:
    return {
        "phone": f"+1415555{suffix[-4:]}",
        "email": f"applicant-{suffix}@example.org",
        "country": "United States",
        "region": "California",
        "password": "StrongPass1",
        "confirm_password": "StrongPass1",
        "accept_terms": True,
        "accept_privacy": True,
        "marketing_consent": False,
        "data": {},
    }


def test_patient_self_registration_is_fixed_to_patient_and_requires_verification() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    payload.update({"first_name": "New", "last_name": "Patient", "role": "platform-admin"})
    payload["data"] = {"date_of_birth": "1994-04-12", "gender": "Female", "city": "Oakland", "emergency_contact_phone": "+14155550123"}
    with TestClient(app) as client:
        response = client.post("/api/v1/signup/patient", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["application_type"] == "patient"
        assert body["onboarding_type"] == "PUBLIC_SELF_REGISTRATION"
        assert body["status"] == "PHONE_VERIFICATION_REQUIRED"
        assert body["dashboard_path"] is None
        status = client.get(f"/api/v1/signup/status/{body['id']}")
    assert status.status_code == 200
    assert status.json()["dashboard_path"] is None


def test_patient_registration_supports_international_phone_numbers() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    payload.update({"first_name": "Global", "last_name": "Patient", "phone": f"+44{int(uuid4().hex[:10], 16) % 10_000_000_000:010d}"})
    payload["data"] = {"date_of_birth": "1988-11-02", "city": "London"}
    with TestClient(app) as client:
        response = client.post("/api/v1/signup/patient", json=payload)
    assert response.status_code == 201, response.text


def test_hospital_application_stays_pending_and_rejects_invalid_coordinates() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    payload["data"] = {
        "legal_name": f"Hospital {suffix}", "registration_number": f"REG-{suffix}", "licence_number": f"LIC-{suffix}",
        "regulatory_authority": "Health Facilities Authority", "official_email": f"admin-{suffix}@hospital.org",
        "administrator_name": "Hospital Administrator", "latitude": "91", "longitude": "7.4",
    }
    with TestClient(app) as client:
        invalid = client.post("/api/v1/signup/hospital", json=payload)
        payload["data"]["latitude"] = "5.1"
        valid = client.post("/api/v1/signup/hospital", json=payload)
    assert invalid.status_code == 422
    assert valid.status_code == 201, valid.text
    assert valid.json()["status"] == "PENDING_FACILITY_VERIFICATION"
    assert valid.json()["dashboard_path"] is None


def test_invitation_only_roles_cannot_self_activate() -> None:
    suffix = uuid4().hex[:8]
    nurse = common_payload(suffix)
    nurse.update({"full_name": "Invited Nurse"})
    nurse["data"] = {"nursing_category": "Registered Nurse", "licence_number": f"RN-{suffix}", "licensing_authority": "Nursing Council", "licence_jurisdiction": "GH"}
    admin = common_payload(uuid4().hex[:8])
    admin.update({"full_name": "Requested Admin"})
    admin["data"] = {"admin_role": "SUPER_ADMIN", "mfa_method": "Security key", "security_policy_acceptance": "ACCEPT"}
    with TestClient(app) as client:
        nurse_response = client.post("/api/v1/signup/nurse", json=nurse)
        admin_response = client.post("/api/v1/signup/platform-admin", json=admin)
    assert nurse_response.status_code == 422
    assert "invitation" in nurse_response.text.lower()
    assert admin_response.status_code == 422
    assert "invitation" in admin_response.text.lower()


def test_government_application_requires_official_authorization_and_domain() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    payload["data"] = {"legal_name": "Health Ministry", "government_level": "State", "jurisdiction": "Example State", "official_email": "officer@gmail.com", "full_name": "Public Officer", "official_title": "Director"}
    with TestClient(app) as client:
        missing_authorization = client.post("/api/v1/signup/government", json=payload)
        payload["data"]["authorization_document_key"] = f"private/government/{suffix}.pdf"
        public_email = client.post("/api/v1/signup/government", json=payload)
    assert missing_authorization.status_code == 422
    assert public_email.status_code == 422
    assert "official domain" in public_email.text.lower()
async def seed_admin_invitation(raw_token: str, email: str) -> None:
    async with app.state.session_factory() as session:
        session.add(StaffInvitation(hospital_id=UUID("11111111-1111-1111-1111-111111111111"), organization_id=UUID("11111111-1111-1111-1111-111111111111"), department_id="Platform", permitted_role="admin", intended_role="SUPPORT_ADMIN", invitation_code=f"legacy-{uuid4().hex}", token_hash=token_hash(raw_token), invited_email=email, expires_at=datetime.now(UTC) + timedelta(hours=1)))
        await session.commit()


def test_platform_admin_invitation_caps_the_requested_role() -> None:
    suffix = uuid4().hex[:8]
    token = f"secure-admin-{uuid4().hex}"
    payload = common_payload(suffix)
    payload.update({"full_name": "Invited Administrator", "invitation_token": token})
    payload["data"] = {"admin_role": "SUPER_ADMIN", "mfa_method": "Security key", "security_policy_acceptance": "ACCEPT"}
    with TestClient(app) as client:
        asyncio.run(seed_admin_invitation(token, payload["email"]))
        response = client.post("/api/v1/signup/platform-admin", json=payload)
    assert response.status_code == 422
    assert "invitation scope" in response.text.lower()
