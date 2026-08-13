import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.auth_service import hash_password, token_hash
from app.main import app
from app.models import AuthAccount, HospitalDepartment, StaffInvitation, StaffMembership, Tenant, Ticket


async def seed_multifacility_specialist() -> dict[str, str]:
    suffix = uuid4().hex[:8]
    account_id = uuid4()
    facility_ids = [uuid4(), uuid4()]
    department_ids = [uuid4(), uuid4()]
    email = f"multi-{suffix}@example.com"
    async with app.state.session_factory() as session:
        account = AuthAccount(
            id=account_id,
            tenant_id=facility_ids[0],
            role="specialist",
            identifier=email,
            password_hash=hash_password("Password123!"),
            first_name="Multi",
            last_name="Facility",
            email=email,
            specialty="Cardiology",
            is_active=True,
        )
        session.add(account)
        for index, facility_id in enumerate(facility_ids):
            session.add(Tenant(id=facility_id, name=f"Facility {suffix}-{index}", state_location="Test State", status="ACTIVE"))
            session.add(HospitalDepartment(id=department_ids[index], hospital_id=facility_id, name="Cardiology", code=f"CARD-{suffix}-{index}", status="ACTIVE"))
        memberships = [
            StaffMembership(user_id=account_id, hospital_id=facility_ids[0], department_id="Cardiology", department_ref_id=department_ids[0], role="specialist", specialty_id="Cardiology", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True),
            StaffMembership(user_id=account_id, hospital_id=facility_ids[1], department_id="Cardiology", department_ref_id=department_ids[1], role="specialist", specialty_id="Cardiology", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True),
            StaffMembership(user_id=account_id, hospital_id=facility_ids[1], department_id="Neurology", role="specialist", specialty_id="Neurology", verification_status="SUSPENDED", employment_status="SUSPENDED", is_active=False, is_on_duty=False),
            StaffMembership(user_id=account_id, hospital_id=facility_ids[1], department_id="Emergency", role="specialist", specialty_id="Emergency Medicine", verification_status="PENDING_VERIFICATION", employment_status="ACTIVE", is_active=False, is_on_duty=False),
        ]
        session.add_all(memberships)
        await session.flush()
        ticket = Ticket(
            tenant_id=facility_ids[0],
            routed_tenant_id=facility_ids[1],
            ticket_number=f"MEM-{suffix}",
            customer_phone=f"+23480{suffix[:6]}",
            raw_intake_text="Specialty workspace test",
            assigned_specialty="Neurology",
            urgency_level="ROUTINE",
            queue_status="QUEUED",
        )
        session.add(ticket)
        await session.commit()
        return {
            "email": email,
            "active_second": str(memberships[1].id),
            "suspended": str(memberships[2].id),
            "unverified": str(memberships[3].id),
            "ticket_id": str(ticket.id),
        }


def test_multifacility_workspace_selection_and_membership_states() -> None:
    with TestClient(app) as client:
        seeded = asyncio.run(seed_multifacility_specialist())
        login = client.post("/api/v1/auth/specialist/login", json={"email": seeded["email"], "password": "Password123!"})
        workspaces = client.get("/api/v1/staff/workspaces")
        before_selection = client.get("/api/v1/specialist/dashboard")
        suspended = client.post(f"/api/v1/staff/workspaces/{seeded['suspended']}/select")
        unverified = client.post(f"/api/v1/staff/workspaces/{seeded['unverified']}/select")
        selected = client.post(f"/api/v1/staff/workspaces/{seeded['active_second']}/select")
        cross_department = client.patch(f"/api/v1/specialist/patients/{seeded['ticket_id']}/assign-self")

    assert login.status_code == 200
    assert before_selection.status_code == 409
    states = {item["state"] for item in workspaces.json()}
    assert {"MEMBERSHIP_ACTIVE", "MEMBERSHIP_SUSPENDED", "LICENCE_VERIFICATION_REQUIRED"} <= states
    assert suspended.status_code == 403
    assert unverified.status_code == 403
    assert selected.status_code == 200
    assert cross_department.status_code == 403


def test_expired_staff_invitation_is_rejected() -> None:
    raw_token = f"expired-{uuid4().hex}"

    async def seed() -> str:
        facility_id = uuid4()
        async with app.state.session_factory() as session:
            session.add(Tenant(id=facility_id, name="Expired Invite Facility", state_location="Test State", status="ACTIVE"))
            session.add(StaffInvitation(
                hospital_id=facility_id,
                department_id="Cardiology",
                permitted_role="specialist",
                intended_role="specialist",
                invitation_code=f"expired-{uuid4().hex}",
                token_hash=token_hash(raw_token),
                invited_email="expired@example.com",
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            ))
            await session.commit()
        return str(facility_id)

    with TestClient(app) as client:
        asyncio.run(seed())
        response = client.post("/api/v1/signup/invitations/validate", json={"role": "specialist", "token": raw_token, "email": "expired@example.com"})

    assert response.status_code == 422
    assert "expired" in response.json()["detail"].lower()
