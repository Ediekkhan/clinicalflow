import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import Appointment, AuthAccount, HospitalDoctorMembership, Provider, ProviderSlot, StaffMembership, Tenant, Ticket
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, create_session, hash_password

PHONE = "+2348091111111"
PASSWORD = "Password123!"


async def seed_case(*, specialty="General Medicine", doctor_active=True, verified=True, active_from_offset=-1, provider_specialty=None, provider_has_doctor=True, booked=False, capacity=12, on_duty=True):
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    async with app.state.session_factory() as session:
        hospital = Tenant(name=f"Assignment Hospital {suffix}", state_location="Assignment address", status="ACTIVE", accepts_patients=True, latitude=2.0, longitude=2.0)
        other_hospital = Tenant(name=f"Other Hospital {suffix}", state_location="Other address", status="ACTIVE", accepts_patients=True, latitude=20.0, longitude=20.0)
        session.add_all([hospital, other_hospital])
        await session.flush()
        doctor = AuthAccount(tenant_id=hospital.id, role="doctor", identifier=f"assign-{suffix}:doctor", password_hash=hash_password(PASSWORD), first_name="Assigned", last_name="Doctor", is_active=doctor_active)
        other_doctor = AuthAccount(tenant_id=other_hospital.id, role="doctor", identifier=f"other-{suffix}:doctor", password_hash=hash_password(PASSWORD), first_name="Other", last_name="Doctor", is_active=True)
        session.add_all([doctor, other_doctor])
        await session.flush()
        if verified is not None:
            session.add(HospitalDoctorMembership(hospital_id=hospital.id, doctor_id=doctor.id, specialty_id=specialty, verification_status="VERIFIED" if verified else "PENDING", employment_status="ACTIVE", is_active=True, active_from=now + timedelta(days=active_from_offset)))
            session.add(StaffMembership(user_id=doctor.id, hospital_id=hospital.id, department_id=specialty, role="doctor", specialty_id=specialty, verification_status="VERIFIED" if verified else "PENDING", employment_status="ACTIVE", is_active=True, is_on_duty=on_duty, active_from=now + timedelta(days=active_from_offset)))
        session.add(HospitalDoctorMembership(hospital_id=other_hospital.id, doctor_id=other_doctor.id, specialty_id=specialty, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, active_from=now - timedelta(days=1)))
        session.add(StaffMembership(user_id=other_doctor.id, hospital_id=other_hospital.id, department_id=specialty, role="doctor", specialty_id=specialty, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1)))
        provider = Provider(tenant_id=hospital.id, doctor_id=doctor.id if provider_has_doctor else None, full_name=f"Provider {suffix}", specialty=provider_specialty or specialty, room_label="Room A", max_daily_capacity=capacity, is_active=True)
        other_provider = Provider(tenant_id=other_hospital.id, doctor_id=other_doctor.id, full_name=f"Other Provider {suffix}", specialty=specialty, room_label="Room B", max_daily_capacity=capacity, is_active=True)
        session.add_all([provider, other_provider])
        await session.flush()
        slot = ProviderSlot(tenant_id=hospital.id, provider_id=provider.id, starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=1, minutes=30), is_booked=booked)
        other_slot = ProviderSlot(tenant_id=other_hospital.id, provider_id=other_provider.id, starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=1, minutes=30))
        ticket = Ticket(tenant_id=hospital.id, routed_tenant_id=hospital.id, ticket_number=f"TEST-{suffix}", customer_phone=PHONE, raw_intake_text="Assignment test", channel="WEB", urgency_level="URGENT", matched_condition_id="test", assigned_specialty=specialty, queue_status="QUEUED")
        session.add_all([slot, other_slot, ticket])
        await session.flush()
        if capacity == 0:
            session.add(Appointment(tenant_id=hospital.id, hospital_id=hospital.id, ticket_id=ticket.id, doctor_id=doctor.id, specialty_id=specialty, slot_id=slot.id, customer_phone=PHONE, urgency="URGENT", starts_at=slot.starts_at, ends_at=slot.ends_at, status="BOOKED"))
        doctor_session = await create_session(session, doctor)
        other_session = await create_session(session, other_doctor)
        await session.commit()
        return {"hospital": hospital.id, "other_hospital": other_hospital.id, "doctor": doctor.id, "other_doctor": other_doctor.id, "slot": slot.id, "other_slot": other_slot.id, "ticket": ticket.id, "doctor_tokens": doctor_session, "other_tokens": other_session, "specialty": specialty}


def use_session(client: TestClient, issued) -> None:
    client.cookies.set(ACCESS_COOKIE, issued.access_token)
    client.cookies.set(REFRESH_COOKIE, issued.refresh_token)


def book(client: TestClient, fixture, slot_key="slot"):
    return client.post("/api/v1/appointments", json={"ticket_id": str(fixture["ticket"]), "slot_id": str(fixture[slot_key]), "customer_phone": PHONE})


def test_destination_hospital_verified_doctor_can_be_assigned_and_notified() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        response = book(client, fixture)
        assert response.status_code == 201
        appointment = response.json()
        assert appointment["hospital_id"] == str(fixture["hospital"])
        assert appointment["doctor_id"] == str(fixture["doctor"])
        use_session(client, fixture["doctor_tokens"])
        notifications = client.get("/api/v1/notifications").json()
        appointments = client.get("/api/v1/appointments").json()
        assert any(row.get("appointment_id") == appointment["id"] and row["type"] == "appointment.assigned" for row in notifications)
        assert [row["id"] for row in appointments] == [appointment["id"]]
        client.post("/api/v1/auth/logout")
        use_session(client, fixture["other_tokens"])
        assert all(row.get("appointment_id") != appointment["id"] for row in client.get("/api/v1/notifications").json())
        assert client.get("/api/v1/appointments").json() == []


def test_cross_hospital_wrong_specialty_inactive_unverified_off_duty_and_booked_slots_rejected() -> None:
    cases = [
        ({}, "other_slot"),
        ({"provider_specialty": "Pediatrics"}, "slot"),
        ({"doctor_active": False}, "slot"),
        ({"verified": False}, "slot"),
        ({"active_from_offset": 2}, "slot"),
        ({"on_duty": False}, "slot"),
        ({"booked": True}, "slot"),
    ]
    with TestClient(app) as client:
        for kwargs, slot_key in cases:
            fixture = asyncio.run(seed_case(**kwargs))
            assert book(client, fixture, slot_key).status_code == 409


def test_eligible_doctor_gets_unassigned_request_and_first_accept_locks_assignment() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case(provider_has_doctor=False))
        assert book(client, fixture).status_code == 409
        use_session(client, fixture["doctor_tokens"])
        assert any(row["type"] == "reassignment.requested" for row in client.get("/api/v1/notifications").json())

        async def create_unassigned():
            async with app.state.session_factory() as session:
                slot = await session.get(ProviderSlot, fixture["slot"])
                appointment = Appointment(tenant_id=fixture["hospital"], hospital_id=fixture["hospital"], department_id=fixture["specialty"], ticket_id=fixture["ticket"], doctor_id=None, specialty_id=fixture["specialty"], slot_id=fixture["slot"], customer_phone=PHONE, urgency="URGENT", starts_at=slot.starts_at, ends_at=slot.ends_at, status="AWAITING_CLINICAL_REVIEW")
                session.add(appointment)
                await session.commit()
                return appointment.id
        appointment_id = asyncio.run(create_unassigned())
        accepted = client.post(f"/api/v1/appointments/{appointment_id}/accept")
        assert accepted.status_code == 200
        client.post("/api/v1/auth/logout")
        use_session(client, fixture["other_tokens"])
        assert client.post(f"/api/v1/appointments/{appointment_id}/accept").status_code == 404


def test_reschedule_and_cancellation_notify_assigned_doctor() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        appointment = book(client, fixture).json()
        use_session(client, fixture["doctor_tokens"])
        cancelled = client.patch(f"/api/v1/appointments/{appointment['id']}/cancel")
        assert cancelled.status_code == 200
        notifications = client.get("/api/v1/notifications").json()
        assert any(row["type"] == "appointment.cancelled" for row in notifications)
