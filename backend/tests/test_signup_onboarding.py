import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuthAccount, HospitalDepartment, SignupApplication, StaffInvitation, StaffMembership, Tenant
from app.services.auth_service import token_hash


def common_payload(suffix: str) -> dict:
    return {
        "phone": f"+1{int(suffix, 16) % 10_000_000_000:010d}",
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


def test_staff_and_admin_roles_cannot_bypass_membership_controls() -> None:
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
    assert "registered hospital" in nurse_response.text.lower() or "required fields" in nurse_response.text.lower()
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

async def seed_registered_hospital(suffix: str) -> tuple[UUID, str]:
    hospital_id = uuid4()
    department_name = f"Department {suffix}"
    async with app.state.session_factory() as session:
        session.add(Tenant(id=hospital_id, name=f"Registered Hospital {suffix}", state_location="Test State", status="ACTIVE"))
        session.add(HospitalDepartment(hospital_id=hospital_id, name=department_name, code=f"DEP-{suffix}", status="ACTIVE"))
        await session.commit()
    return hospital_id, department_name


async def load_staff_application(application_id: UUID) -> tuple[SignupApplication, AuthAccount, StaffMembership]:
    async with app.state.session_factory() as session:
        application = await session.get(SignupApplication, application_id)
        assert application and application.account_id
        account = await session.get(AuthAccount, application.account_id)
        membership = await session.scalar(select(StaffMembership).where(StaffMembership.user_id == application.account_id))
        assert account and membership
        session.expunge(application)
        session.expunge(account)
        session.expunge(membership)
        return application, account, membership


def test_nurse_join_request_creates_inactive_personal_account_and_pending_membership() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    payload.update({"full_name": "Pending Staff Member"})
    with TestClient(app) as client:
        hospital_id, department = asyncio.run(seed_registered_hospital(suffix))
        payload["data"] = {
            "onboarding_method": "JOIN_REQUEST",
            "registered_hospital_id": str(hospital_id),
            "department_id": department,
            "employment_type": "Full time",
            "employee_number": f"EMP-{suffix}",
            "nursing_category": "Registered Nurse",
            "nursing_focus": "Emergency Nursing",
            "licence_number": f"RN-{suffix}",
            "licensing_authority": "Nursing Council",
            "licence_jurisdiction": "NG",
        }
        response = client.post("/api/v1/signup/nurse", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "PENDING_HOSPITAL_APPROVAL"
    application, account, membership = asyncio.run(load_staff_application(UUID(response.json()["id"])))
    assert application.account_id == account.id
    assert account.tenant_id != hospital_id
    assert account.is_active is False
    assert membership.hospital_id == hospital_id
    assert membership.department_id == department
    assert membership.role == "nurse"
    assert membership.verification_status == "PENDING_HOSPITAL_APPROVAL"
    assert membership.employment_status == "PENDING"
    assert membership.is_active is False
async def seed_staff_invitation(hospital_id: UUID, department: str, token: str, email: str) -> None:
    async with app.state.session_factory() as session:
        session.add(StaffInvitation(hospital_id=hospital_id, organization_id=hospital_id, department_id=department, permitted_role="doctor", intended_role="doctor", specialty_id="Cardiology", employment_type="Full time", invitation_code=f"staff-{uuid4().hex}", token_hash=token_hash(token), invited_email=email, expires_at=datetime.now(UTC) + timedelta(days=1)))
        await session.commit()


def test_staff_invitation_fixes_hospital_department_role_and_specialty() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    payload.update({"full_name": "Invited Clinician"})
    with TestClient(app) as client:
        hospital_id, department = asyncio.run(seed_registered_hospital(suffix))
        raw_token = f"secure-staff-{uuid4().hex}"
        asyncio.run(seed_staff_invitation(hospital_id, department, raw_token, payload["email"]))
        payload["invitation_token"] = raw_token
        payload["data"] = {
            "onboarding_method": "INVITATION",
            "professional_title": "Doctor",
            "primary_specialty": "Neurology",
            "licence_number": f"MED-{suffix}",
            "licensing_authority": "Medical Council",
            "licence_jurisdiction": "NG",
        }
        response = client.post("/api/v1/signup/specialist", json=payload)
    assert response.status_code == 201, response.text
    _application, account, membership = asyncio.run(load_staff_application(UUID(response.json()["id"])))
    assert account.tenant_id != hospital_id
    assert membership.hospital_id == hospital_id
    assert membership.department_id == department
    assert membership.role == "doctor"
    assert membership.specialty_id == "Cardiology"
    assert membership.is_active is False
async def seed_platform_reviewer() -> tuple[str, str]:
    from app.models import AuthAccount, Tenant
    from app.services.auth_service import create_session, hash_password

    async with app.state.session_factory() as session:
        tenant = Tenant(id=uuid4(), name="Platform Review Workspace", state_location="Platform", status="ACTIVE")
        session.add(tenant)
        await session.flush()
        account = AuthAccount(tenant_id=tenant.id, role="admin", identifier=f"reviewer-{uuid4().hex}@example.org", password_hash=hash_password("StrongPass1"), first_name="Platform", last_name="Reviewer", email=f"reviewer-{uuid4().hex}@example.org", is_active=True)
        session.add(account)
        await session.flush()
        issued = await create_session(session, account)
        await session.commit()
        return issued.access_token, issued.refresh_token


def test_platform_approval_provisions_facility_admin_workspace() -> None:
    suffix = uuid4().hex[:8]
    payload = common_payload(suffix)
    admin_email = f"facility-admin-{suffix}@hospital.org"
    payload["data"] = {
        "legal_name": f"Provisioned Hospital {suffix}",
        "registration_number": f"REG-{suffix}",
        "licence_number": f"LIC-{suffix}",
        "regulatory_authority": "Health Facilities Authority",
        "official_email": admin_email,
        "administrator_name": "Provisioned Administrator",
        "latitude": "5.2",
        "longitude": "7.5",
    }
    with TestClient(app) as client:
        application = client.post("/api/v1/signup/hospital", json=payload)
        assert application.status_code == 201, application.text
        access_token, refresh_token = asyncio.run(seed_platform_reviewer())
        client.cookies.set("synaptiverse_access", access_token)
        client.cookies.set("synaptiverse_refresh", refresh_token)
        approved = client.patch(f"/api/v1/platform/signup-applications/{application.json()['id']}/review", json={"decision": "APPROVE"})
        assert approved.status_code == 200, approved.text
        client.cookies.clear()
        login = client.post("/api/v1/auth/hospital_admin/login", json={"email": admin_email, "password": "StrongPass1"})
        hospitals = client.get("/api/v1/signup/registered-hospitals")
    body = approved.json()
    assert body["status"] == "ACTIVE"
    assert body["tenant_id"]
    assert login.status_code == 200, login.text
    assert login.json()["tenant_id"] == body["tenant_id"]
    assert any(item["id"] == body["tenant_id"] for item in hospitals.json()["items"])
