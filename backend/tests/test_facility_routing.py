import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuthAccount, Provider, ProviderSlot, Tenant, Ticket
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, create_session, hash_password
from app.services.facility_routing import haversine_km, select_nearest_eligible_hospital
from app.services.knowledge_graph import fallback_route

PATIENT_PHONE = "+2348012345678"
PASSWORD = "Password123!"


def test_haversine_returns_zero_for_same_coordinates() -> None:
    assert haversine_km(5.0, 7.0, 5.0, 7.0) == 0


async def seed_routing_fixture() -> dict[str, object]:
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    base_latitude = 30 + (int(suffix[:2], 16) / 1000)
    base_longitude = 30 + (int(suffix[2:4], 16) / 1000)
    patient_latitude = base_latitude + 0.01
    patient_longitude = base_longitude + 0.01
    async with app.state.session_factory() as session:
        near = Tenant(name=f"Route Test Near {suffix}", state_location="Near test address", latitude=base_latitude, longitude=base_longitude, status="ACTIVE", accepts_patients=True)
        far = Tenant(name=f"Route Test Far {suffix}", state_location="Far test address", latitude=base_latitude + 5, longitude=base_longitude + 5, status="ACTIVE", accepts_patients=True)
        inactive = Tenant(name=f"Route Test Inactive {suffix}", state_location="Inactive test address", latitude=patient_latitude, longitude=patient_longitude, status="INACTIVE", accepts_patients=True)
        missing_coords = Tenant(name=f"Route Test Missing Coords {suffix}", state_location="Missing coords", status="ACTIVE", accepts_patients=True)
        session.add_all([near, far, inactive, missing_coords])
        await session.flush()
        provider = Provider(tenant_id=near.id, full_name=f"Routing Doctor {suffix}", specialty="General Medicine", room_label="Room 1", is_active=True)
        session.add(provider)
        await session.flush()
        slot = ProviderSlot(tenant_id=near.id, provider_id=provider.id, starts_at=now + timedelta(hours=2), ends_at=now + timedelta(hours=2, minutes=30), is_locked=False, is_booked=False)
        near_admin = AuthAccount(tenant_id=near.id, role="hospital_admin", identifier=f"route-near-{suffix}:hospital_admin", password_hash=hash_password(PASSWORD), first_name="Route", last_name="Near", email=f"near-{suffix}@example.test")
        far_admin = AuthAccount(tenant_id=far.id, role="hospital_admin", identifier=f"route-far-{suffix}:hospital_admin", password_hash=hash_password(PASSWORD), first_name="Route", last_name="Far", email=f"far-{suffix}@example.test")
        session.add_all([slot, near_admin, far_admin])
        await session.flush()
        near_session = await create_session(session, near_admin)
        far_session = await create_session(session, far_admin)
        await session.commit()
        return {
            "near": near.id,
            "far": far.id,
            "inactive": inactive.id,
            "missing_coords": missing_coords.id,
            "near_access": near_session.access_token,
            "near_refresh": near_session.refresh_token,
            "far_access": far_session.access_token,
            "far_refresh": far_session.refresh_token,
            "patient_latitude": patient_latitude,
            "patient_longitude": patient_longitude,
        }


def staff_client(access_token: str, refresh_token: str) -> TestClient:
    client = TestClient(app)
    client.__enter__()
    client.cookies.set(ACCESS_COOKIE, access_token)
    client.cookies.set(REFRESH_COOKIE, refresh_token)
    return client


def test_nearest_service_uses_active_registered_hospital_with_coordinates() -> None:
    with TestClient(app):
        fixture = asyncio.run(seed_routing_fixture())
        async def select_route():
            async with app.state.session_factory() as session:
                return await select_nearest_eligible_hospital(session, fixture["patient_latitude"], fixture["patient_longitude"], fallback_route(["fever"]))
        route = asyncio.run(select_route())

    assert route is not None
    assert route.tenant.id == fixture["near"]
    assert route.tenant.id != fixture["inactive"]
    assert route.tenant.id != fixture["missing_coords"]
    assert route.distance_km > 0
    assert route.provider is not None


def test_patient_triage_requires_valid_coordinates() -> None:
    with TestClient(app) as client:
        assert client.post("/api/v1/auth/patient/login", json={"phone": PATIENT_PHONE, "password": PASSWORD}).status_code == 200
        missing = client.post("/api/v1/patient/triage", json={"symptom_description": "I have fever and weakness"})
        invalid = client.post("/api/v1/patient/triage", json={"symptom_description": "I have fever and weakness", "latitude": 95, "longitude": 7})

    assert missing.status_code == 422
    assert "location is required" in missing.json()["detail"]
    assert invalid.status_code == 422
    assert "outside the valid" in invalid.json()["detail"]


def test_patient_triage_persists_destination_and_enforces_ticket_visibility() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_routing_fixture())
        assert client.post("/api/v1/auth/patient/login", json={"phone": PATIENT_PHONE, "password": PASSWORD}).status_code == 200
        response = client.post(
            "/api/v1/patient/triage",
            json={"symptom_description": "I have fever and weakness", "latitude": fixture["patient_latitude"], "longitude": fixture["patient_longitude"]},
        )
        patient_tickets = client.get("/api/v1/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert payload["nearest_clinic"]["tenant_id"] == str(fixture["near"])
    assert payload["nearest_clinic"]["distance_km"] >= 0
    ticket_id = payload["ticket"]["id"]
    patient_ticket = next(ticket for ticket in patient_tickets.json() if ticket["id"] == ticket_id)
    assert patient_ticket["routed_tenant_id"] == str(fixture["near"])
    assert patient_ticket["patient_latitude"] == fixture["patient_latitude"]
    assert patient_ticket["patient_longitude"] == fixture["patient_longitude"]
    assert patient_ticket["route_distance_km"] is not None

    near_client = staff_client(fixture["near_access"], fixture["near_refresh"])
    try:
        destination_tickets = near_client.get("/api/v1/tickets")
        assert destination_tickets.status_code == 200
        assert any(ticket["id"] == ticket_id for ticket in destination_tickets.json())
    finally:
        near_client.__exit__(None, None, None)

    far_client = staff_client(fixture["far_access"], fixture["far_refresh"])
    try:
        unrelated_tickets = far_client.get("/api/v1/tickets")
        assert unrelated_tickets.status_code == 200
        assert all(ticket["id"] != ticket_id for ticket in unrelated_tickets.json())
    finally:
        far_client.__exit__(None, None, None)


def test_legacy_tenant_owned_ticket_remains_visible_to_owner_staff() -> None:
    with TestClient(app) as client:
        created = client.post("/api/v1/tickets", json={"customer_phone": "+2348070000000", "raw_intake_text": "Routine headache", "channel": "WEB"})
        ticket_id = created.json()["id"]
        client.post("/api/v1/auth/staff/pin-login", json={"role": "nurse", "pin": "2468"})
        tickets = client.get("/api/v1/tickets")

    assert created.status_code == 201
    assert tickets.status_code == 200
    assert any(ticket["id"] == ticket_id for ticket in tickets.json())



