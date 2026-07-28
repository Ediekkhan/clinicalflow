import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import AuthAccount, FacilityAcceptance, FacilityRegistry, StaffMembership, Tenant, Ticket
from app.services.auth_service import create_session, hash_password

PASSWORD = "StrongPass1"


async def seed_facility_workspace(suffix: str, *, accepts_patients: bool = True) -> dict[str, str]:
    async with app.state.session_factory() as session:
        tenant = Tenant(id=uuid4(), name=f"Facility {suffix}", state_location="Test State", latitude=5.0, longitude=7.0, accepts_patients=accepts_patients, status="ACTIVE")
        session.add(tenant)
        await session.flush()
        session.add(FacilityRegistry(tenant_id=tenant.id, facility_type="HOSPITAL", country="NG", jurisdiction="Test State", status="ACTIVE", accepts_patients=accepts_patients))
        account = AuthAccount(tenant_id=tenant.id, role="hospital_admin", identifier=f"facility-admin-{suffix}@example.org", password_hash=hash_password(PASSWORD), first_name="Facility", last_name="Admin", email=f"facility-admin-{suffix}@example.org", is_active=True)
        session.add(account)
        await session.flush()
        membership = StaffMembership(user_id=account.id, hospital_id=tenant.id, department_id="Administration", role="hospital_admin", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=datetime.now(UTC) - timedelta(days=1))
        session.add(membership)
        issued = await create_session(session, account)
        await session.commit()
        return {"tenant_id": str(tenant.id), "account_id": str(account.id), "access": issued.access_token, "refresh": issued.refresh_token}


async def seed_routed_ticket(facility_id: str, suffix: str, status: str = "AWAITING_FACILITY_ACCEPTANCE") -> str:
    async with app.state.session_factory() as session:
        ticket = Ticket(tenant_id=UUID(facility_id), routed_tenant_id=UUID(facility_id), ticket_number=f"FAC-{suffix}", customer_phone=f"+23470{suffix[:8]}", raw_intake_text="Facility acceptance test", channel="WEB", urgency_level="URGENT", matched_condition_id="test", assigned_specialty="General Medicine", queue_status=status)
        session.add(ticket)
        await session.commit()
        return str(ticket.id)


def authenticate(client: TestClient, workspace: dict[str, str]) -> None:
    client.cookies.set("synaptiverse_access", workspace["access"])
    client.cookies.set("synaptiverse_refresh", workspace["refresh"])


def test_facility_accepts_routed_ticket_then_validates_queue_transitions() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        facility = asyncio.run(seed_facility_workspace(suffix))
        ticket_id = asyncio.run(seed_routed_ticket(facility["tenant_id"], suffix))
        authenticate(client, facility)
        accepted = client.post(f"/api/v1/hospital/tickets/{ticket_id}/facility-decision", json={"decision": "ACCEPT"})
        invalid = client.post(f"/api/v1/hospital/tickets/{ticket_id}/transition", json={"status": "BEING_SEEN"})
        travelling = client.post(f"/api/v1/hospital/tickets/{ticket_id}/transition", json={"status": "TRAVELLING"})
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["ticket"]["queue_status"] == "ACCEPTED"
    assert invalid.status_code == 409
    assert travelling.status_code == 200, travelling.text
    assert travelling.json()["queue_status"] == "TRAVELLING"


def test_rejection_and_redirection_require_clear_reasons() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        facility = asyncio.run(seed_facility_workspace(suffix))
        ticket_id = asyncio.run(seed_routed_ticket(facility["tenant_id"], suffix))
        authenticate(client, facility)
        rejected = client.post(f"/api/v1/hospital/tickets/{ticket_id}/facility-decision", json={"decision": "REJECT", "reason": "bad"})
    assert rejected.status_code == 422


async def redirected_ticket_state(ticket_id: str) -> tuple[str, str, str]:
    async with app.state.session_factory() as session:
        ticket = await session.get(Ticket, UUID(ticket_id))
        acceptance = await session.scalar(select(FacilityAcceptance).where(FacilityAcceptance.ticket_id == UUID(ticket_id), FacilityAcceptance.decision == "REDIRECT"))
        assert ticket and acceptance and acceptance.redirected_facility_id
        return ticket.queue_status, str(ticket.routed_tenant_id), str(acceptance.redirected_facility_id)


def test_redirection_moves_ticket_to_destination_facility_for_acceptance() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        origin = asyncio.run(seed_facility_workspace(f"origin-{suffix}"))
        destination = asyncio.run(seed_facility_workspace(f"dest-{suffix}"))
        ticket_id = asyncio.run(seed_routed_ticket(origin["tenant_id"], suffix))
        authenticate(client, origin)
        redirected = client.post(
            f"/api/v1/hospital/tickets/{ticket_id}/facility-decision",
            json={"decision": "REDIRECT", "reason": "No available emergency capacity", "redirect_facility_id": destination["tenant_id"]},
        )
    assert redirected.status_code == 201, redirected.text
    status, routed_tenant_id, redirected_facility_id = asyncio.run(redirected_ticket_state(ticket_id))
    assert status == "AWAITING_FACILITY_ACCEPTANCE"
    assert routed_tenant_id == destination["tenant_id"]
    assert redirected_facility_id == destination["tenant_id"]
    with TestClient(app) as client:
        authenticate(client, destination)
        accepted = client.post(f"/api/v1/hospital/tickets/{ticket_id}/facility-decision", json={"decision": "ACCEPT"})
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["ticket"]["queue_status"] == "ACCEPTED"


def test_redirection_rejects_facilities_that_do_not_accept_patients() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        origin = asyncio.run(seed_facility_workspace(f"origin-{suffix}"))
        destination = asyncio.run(seed_facility_workspace(f"closed-{suffix}", accepts_patients=False))
        ticket_id = asyncio.run(seed_routed_ticket(origin["tenant_id"], suffix))
        authenticate(client, origin)
        response = client.post(
            f"/api/v1/hospital/tickets/{ticket_id}/facility-decision",
            json={"decision": "REDIRECT", "reason": "No available emergency capacity", "redirect_facility_id": destination["tenant_id"]},
        )
    assert response.status_code == 422



