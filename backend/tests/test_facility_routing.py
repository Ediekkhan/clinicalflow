import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import AuthAccount, FacilityRegistry, FacilityService, Provider, ProviderSlot, RoutingCandidate, RoutingDecision, StaffMembership, Tenant, Ticket
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
    patient_latitude = base_latitude
    patient_longitude = base_longitude
    async with app.state.session_factory() as session:
        near = Tenant(name=f"Route Test Near {suffix}", state_location="Near test address", latitude=base_latitude, longitude=base_longitude, status="ACTIVE", accepts_patients=True)
        far = Tenant(name=f"Route Test Far {suffix}", state_location="Far test address", latitude=base_latitude + 5, longitude=base_longitude + 5, status="ACTIVE", accepts_patients=True)
        inactive = Tenant(name=f"Route Test Inactive {suffix}", state_location="Inactive test address", latitude=patient_latitude, longitude=patient_longitude, status="INACTIVE", accepts_patients=True)
        missing_coords = Tenant(name=f"Route Test Missing Coords {suffix}", state_location="Missing coords", status="ACTIVE", accepts_patients=True)
        session.add_all([near, far, inactive, missing_coords])
        await session.flush()
        near_registry = FacilityRegistry(tenant_id=near.id, facility_type="HOSPITAL", country="NG", emergency_capable=True, status="ACTIVE", accepts_patients=True)
        far_registry = FacilityRegistry(tenant_id=far.id, facility_type="HOSPITAL", country="NG", emergency_capable=True, status="ACTIVE", accepts_patients=True)
        session.add_all([near_registry, far_registry])
        await session.flush()
        session.add(FacilityService(facility_registry_id=near_registry.id, service_code="General Medicine", specialty_code="General Medicine", status="ACTIVE"))
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
    assert route.distance_km >= 0
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
async def seed_capability_ranking_fixture(*, near_capacity: str = "AVAILABLE") -> dict[str, object]:
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    latitude, longitude = 45.0 + int(suffix[:2], 16) / 10000, 10.0 + int(suffix[2:4], 16) / 10000
    async with app.state.session_factory() as session:
        near = Tenant(name=f"Capability Near {suffix}", state_location="Near", latitude=latitude, longitude=longitude, status="ACTIVE", accepts_patients=True)
        far = Tenant(name=f"Capability Far {suffix}", state_location="Far", latitude=latitude + 0.2, longitude=longitude + 0.2, status="ACTIVE", accepts_patients=True)
        session.add_all([near, far]); await session.flush()
        near_registry = FacilityRegistry(tenant_id=near.id, facility_type="HOSPITAL", country="NG", emergency_capable=False, capacity_status=near_capacity, status="ACTIVE", accepts_patients=True)
        far_registry = FacilityRegistry(tenant_id=far.id, facility_type="HOSPITAL", country="NG", emergency_capable=True, capacity_status="AVAILABLE", status="ACTIVE", accepts_patients=True)
        session.add_all([near_registry, far_registry]); await session.flush()
        session.add_all([FacilityService(facility_registry_id=near_registry.id, service_code="Dermatology", specialty_code="Dermatology", status="ACTIVE"), FacilityService(facility_registry_id=far_registry.id, service_code="Cardiology", specialty_code="Cardiology", status="ACTIVE")])
        doctor = Provider(tenant_id=far.id, full_name=f"Capability Doctor {suffix}", specialty="Cardiology", room_label="Room C", is_active=True)
        session.add(doctor); await session.flush()
        session.add(ProviderSlot(tenant_id=far.id, provider_id=doctor.id, starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=2), is_locked=False, is_booked=False))
        await session.commit()
        return {"near": near.id, "far": far.id, "latitude": latitude, "longitude": longitude}


def test_farther_capable_facility_beats_nearest_wrong_specialty() -> None:
    with TestClient(app):
        fixture = asyncio.run(seed_capability_ranking_fixture())
        async def route():
            async with app.state.session_factory() as session:
                clinical = SimpleNamespace(target_specialty="Cardiology", derived_urgency="URGENT")
                return await select_nearest_eligible_hospital(session, fixture["latitude"], fixture["longitude"], clinical)
        selected = asyncio.run(route())
    assert selected is not None
    assert selected.tenant.id == fixture["far"]
    near = next(item for item in selected.candidates if item.tenant.id == fixture["near"])
    assert not near.eligible
    assert any("specialty" in reason.lower() for reason in near.reasons)


def test_critical_routing_requires_emergency_capability() -> None:
    with TestClient(app):
        fixture = asyncio.run(seed_capability_ranking_fixture())
        async def route():
            async with app.state.session_factory() as session:
                clinical = SimpleNamespace(target_specialty="Cardiology", derived_urgency="CRITICAL")
                return await select_nearest_eligible_hospital(session, fixture["latitude"], fixture["longitude"], clinical)
        selected = asyncio.run(route())
    assert selected is not None
    assert selected.tenant.id != fixture["near"]
    assert next(item for item in selected.candidates if item.tenant.id == selected.tenant.id).has_emergency_capability


def test_patient_preference_cannot_make_ineligible_facility_routable() -> None:
    with TestClient(app):
        fixture = asyncio.run(seed_capability_ranking_fixture(near_capacity="FULL"))
        async def route():
            async with app.state.session_factory() as session:
                clinical = SimpleNamespace(target_specialty="Cardiology", derived_urgency="URGENT")
                return await select_nearest_eligible_hospital(session, fixture["latitude"], fixture["longitude"], clinical, preferred_facility_id=fixture["near"])
        selected = asyncio.run(route())
    assert selected is not None
    assert selected.tenant.id != fixture["near"]

def test_no_suitable_facility_returns_none_and_cross_country_distance_is_valid() -> None:
    assert haversine_km(6.5244, 3.3792, 51.5072, -0.1276) > 1000
    with TestClient(app):
        fixture = asyncio.run(seed_capability_ranking_fixture())
        async def route():
            async with app.state.session_factory() as session:
                clinical = SimpleNamespace(target_specialty=f"Rare-{uuid4().hex}", derived_urgency="URGENT")
                return await select_nearest_eligible_hospital(session, fixture["latitude"], fixture["longitude"], clinical)
        assert asyncio.run(route()) is None


async def seed_manual_override_fixture() -> dict[str, str]:
    suffix = uuid4().hex[:8]; now = datetime.now(UTC)
    async with app.state.session_factory() as session:
        first = Tenant(name=f"Override A {suffix}", state_location="A", latitude=55.0, longitude=12.0, status="ACTIVE", accepts_patients=True)
        second = Tenant(name=f"Override B {suffix}", state_location="B", latitude=55.1, longitude=12.1, status="ACTIVE", accepts_patients=True)
        session.add_all([first, second]); await session.flush()
        registries = [FacilityRegistry(tenant_id=item.id, facility_type="HOSPITAL", country="NG", emergency_capable=True, status="ACTIVE", accepts_patients=True) for item in (first, second)]
        session.add_all(registries); await session.flush()
        for tenant, registry in zip((first, second), registries):
            session.add(FacilityService(facility_registry_id=registry.id, service_code="Cardiology", specialty_code="Cardiology", status="ACTIVE"))
            provider = Provider(tenant_id=tenant.id, full_name=f"Override Doctor {suffix}", specialty="Cardiology", room_label="Room", is_active=True); session.add(provider); await session.flush()
            session.add(ProviderSlot(tenant_id=tenant.id, provider_id=provider.id, starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=2), is_locked=False, is_booked=False))
        admin = AuthAccount(tenant_id=first.id, role="hospital_admin", identifier=f"override-{suffix}@example.test", password_hash=hash_password(PASSWORD), first_name="Route", last_name="Admin", is_active=True)
        session.add(admin); await session.flush()
        membership = StaffMembership(user_id=admin.id, hospital_id=first.id, department_id="Administration", role="hospital_admin", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True)
        ticket = Ticket(tenant_id=first.id, routed_tenant_id=first.id, ticket_number=f"OVR-{suffix}", customer_phone=f"+23470{suffix[:6]}", raw_intake_text="Routing override", assigned_specialty="Cardiology", urgency_level="URGENT", queue_status="QUEUED", patient_latitude=55.0, patient_longitude=12.0)
        session.add_all([membership, ticket]); await session.flush()
        decision = RoutingDecision(ticket_id=ticket.id, patient_owner_tenant_id=first.id, selected_facility_id=first.id, required_service="Cardiology", required_specialty="Cardiology", urgency="URGENT", status="SELECTED", selection_reason="Initial clinical ranking")
        session.add(decision); await session.flush()
        session.add_all([RoutingCandidate(routing_decision_id=decision.id, facility_id=first.id, rank=1, eligible=True, distance_km=0, suitability_score=140, has_required_capability=True, has_emergency_capability=True, has_staff_coverage=True, has_capacity=True, reasons_json="[]"), RoutingCandidate(routing_decision_id=decision.id, facility_id=second.id, rank=2, eligible=True, distance_km=12, suitability_score=128, has_required_capability=True, has_emergency_capability=True, has_staff_coverage=True, has_capacity=True, reasons_json="[]")])
        auth = await create_session(session, admin); await session.commit()
        return {"ticket": str(ticket.id), "second": str(second.id), "access": auth.access_token, "refresh": auth.refresh_token}


def test_authorized_manual_override_records_reason() -> None:
    with TestClient(app):
        fixture = asyncio.run(seed_manual_override_fixture())
    client = staff_client(fixture["access"], fixture["refresh"])
    try:
        response = client.patch(f"/api/v1/hospital/tickets/{fixture['ticket']}/routing", json={"facility_id": fixture["second"], "reason": "Patient transport is already coordinated with this facility"})
    finally:
        client.__exit__(None, None, None)
    assert response.status_code == 200
    assert response.json()["status"] == "MANUALLY_OVERRIDDEN"
    assert response.json()["selected_facility_id"] == fixture["second"]
