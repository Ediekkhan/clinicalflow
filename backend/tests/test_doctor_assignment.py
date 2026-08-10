import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import Appointment, AppointmentAssignmentRequest, AuditLog, AuthAccount, CareTeamAssignment, HospitalDoctorMembership, Notification, NotificationDelivery, OutboxEvent, Provider, ProviderSlot, StaffMembership, Tenant, Ticket
from app.routes import TriageConnectionManager, triage_manager
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
        persisted_appointment, personal_notifications = asyncio.run(assigned_notification_links(appointment["id"]))
        assert len(personal_notifications) == 1
        assert personal_notifications[0].recipient_user_id == persisted_appointment.doctor_id
        assert personal_notifications[0].recipient_membership_id == persisted_appointment.staff_membership_id
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
        assert any(row["type"] == "appointment.assignment.requested" for row in client.get("/api/v1/notifications").json())

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

async def seed_same_hospital_staff(fixture, role="doctor", verified=True):
    async with app.state.session_factory() as session:
        suffix = uuid4().hex[:8]
        account = AuthAccount(tenant_id=fixture["hospital"], role=role, identifier=f"peer-{suffix}:{role}", password_hash=hash_password(PASSWORD), first_name="Peer", last_name=role.title(), is_active=True)
        session.add(account)
        await session.flush()
        membership = StaffMembership(user_id=account.id, hospital_id=fixture["hospital"], department_id=fixture["specialty"], role=role, specialty_id=fixture["specialty"] if role != "nurse" else None, verification_status="VERIFIED" if verified else "PENDING", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=datetime.now(UTC) - timedelta(days=1))
        session.add(membership)
        await session.flush()
        issued = await create_session(session, account)
        await session.commit()
        return account.id, membership.id, issued


async def add_care_assignment(fixture, user_id, membership_id, appointment_id, sections):
    async with app.state.session_factory() as session:
        session.add(CareTeamAssignment(hospital_id=fixture["hospital"], department_id=fixture["specialty"], ticket_id=fixture["ticket"], appointment_id=UUID(str(appointment_id)), user_id=user_id, membership_id=membership_id, assignment_type="NURSING_TASK", permitted_sections_json=json.dumps(sections), status="ACTIVE", starts_at=datetime.now(UTC) - timedelta(minutes=1)))
        await session.commit()


async def finish_treatment(fixture, appointment_id):
    async with app.state.session_factory() as session:
        appointment = await session.get(Appointment, UUID(str(appointment_id)))
        ticket = await session.get(Ticket, fixture["ticket"])
        appointment.status = "COMPLETED"
        ticket.queue_status = "RESOLVED"
        await session.commit()


async def access_audits(ticket_id):
    async with app.state.session_factory() as session:
        rows = (await session.execute(select(AuditLog).where(AuditLog.resource_id == ticket_id, AuditLog.action == "PATIENT_RECORD_VIEWED").order_by(AuditLog.id))).scalars().all()
        return [json.loads(row.log_metadata) for row in rows]


async def assigned_notification_links(appointment_id):
    async with app.state.session_factory() as session:
        appointment = await session.get(Appointment, UUID(str(appointment_id)))
        rows = (await session.execute(select(Notification).where(Notification.appointment_id == appointment.id, Notification.event_type == "APPOINTMENT_ASSIGNED"))).scalars().all()
        return appointment, rows

async def delivery_status(appointment_id):
    async with app.state.session_factory() as session:
        appointment = await session.get(Appointment, UUID(str(appointment_id)))
        delivery = await session.scalar(select(NotificationDelivery).join(Notification, Notification.id == NotificationDelivery.notification_id).where(Notification.appointment_id == appointment.id, Notification.recipient_account_id == appointment.doctor_id, NotificationDelivery.channel == "REALTIME"))
        return delivery.status, delivery.attempts


def test_assigned_doctor_record_access_unrelated_denial_and_completed_cutoff() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        appointment = book(client, fixture).json()
        use_session(client, fixture["doctor_tokens"])
        allowed = client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record?sections=identity,triage,clinical_notes")
        assert allowed.status_code == 200, allowed.text
        assert set(allowed.json()["sections"]) == {"identity", "triage", "clinical_notes"}
        use_session(client, fixture["other_tokens"])
        denied = client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record")
        assert denied.status_code in {403, 404}
        asyncio.run(finish_treatment(fixture, appointment["id"]))
        use_session(client, fixture["doctor_tokens"])
        completed = client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record")
        assert completed.status_code == 403
    audits = asyncio.run(access_audits(fixture["ticket"]))
    assert any(row["outcome"] == "ALLOWED" for row in audits)
    assert sum(row["outcome"] == "DENIED" for row in audits) >= 2


def test_nurse_gets_only_assigned_nursing_sections() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        appointment = book(client, fixture).json()
        nurse_id, membership_id, nurse_tokens = asyncio.run(seed_same_hospital_staff(fixture, "nurse"))
        asyncio.run(add_care_assignment(fixture, nurse_id, membership_id, appointment["id"], ["identity", "allergies", "care_plans"]))
        use_session(client, nurse_tokens)
        allowed = client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record?sections=identity,allergies")
        assert allowed.status_code == 200, allowed.text
        assert client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record?sections=clinical_notes").status_code == 403


def test_break_glass_requires_reason_is_temporary_and_audited() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        _peer_id, _membership_id, peer_tokens = asyncio.run(seed_same_hospital_staff(fixture, "doctor"))
        use_session(client, peer_tokens)
        assert client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record").status_code in {403, 404}
        assert client.post(f"/api/v1/clinician/patients/{fixture['ticket']}/break-glass", json={"reason": "urgent", "confirmed": True}).status_code == 422
        granted = client.post(f"/api/v1/clinician/patients/{fixture['ticket']}/break-glass", json={"reason": "Immediate emergency stabilization requires medication history", "confirmed": True})
        assert granted.status_code == 201, granted.text
        record = client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record?sections=current_medications")
        assert record.status_code == 200
        assert record.json()["relationship"] == "BREAK_GLASS"
    audits = asyncio.run(access_audits(fixture["ticket"]))
    assert any(row["break_glass_used"] is True and row["outcome"] == "ALLOWED" for row in audits)


def test_realtime_failure_keeps_confirmed_appointment_and_schedules_retry(monkeypatch) -> None:
    async def fail_broadcast(*_args, **_kwargs):
        raise RuntimeError("broker unavailable")
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        monkeypatch.setattr(triage_manager, "broadcast", fail_broadcast)
        response = book(client, fixture)
        assert response.status_code == 201, response.text
        status, attempts = asyncio.run(delivery_status(response.json()["id"]))
        assert status == "RETRY_PENDING"
        assert attempts == 1

class FakeSocket:
    def __init__(self):
        self.events = []

    async def accept(self):
        return None

    async def send_json(self, event):
        self.events.append(event)


def test_personal_websocket_event_reaches_only_target_account() -> None:
    async def scenario():
        manager = TriageConnectionManager()
        assigned_socket, unrelated_socket = FakeSocket(), FakeSocket()
        await manager.connect("hospital", "assigned", assigned_socket)
        await manager.connect("hospital", "unrelated", unrelated_socket)
        await manager.broadcast_local("hospital", {"type": "APPOINTMENT_ASSIGNED", "recipient_account_id": "assigned", "payload": {"appointment_id": "appointment"}})
        return assigned_socket.events, unrelated_socket.events
    assigned_events, unrelated_events = asyncio.run(scenario())
    assert len(assigned_events) == 1
    assert unrelated_events == []

def test_unverified_same_hospital_doctor_cannot_open_record() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        book(client, fixture)
        _account_id, _membership_id, issued = asyncio.run(seed_same_hospital_staff(fixture, "doctor", verified=False))
        use_session(client, issued)
        response = client.get(f"/api/v1/clinician/patients/{fixture['ticket']}/record")
        assert response.status_code in {403, 404}
    audits = asyncio.run(access_audits(fixture["ticket"]))
    assert any(row["outcome"] == "DENIED" for row in audits)

async def notification_outbox(appointment_id):
    async with app.state.session_factory() as session:
        notification = await session.scalar(select(Notification).where(Notification.appointment_id == UUID(str(appointment_id)), Notification.event_type == "APPOINTMENT_ASSIGNED"))
        outbox = await session.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == notification.id))
        return notification, outbox


async def assignment_requests(ticket_id):
    async with app.state.session_factory() as session:
        return list((await session.execute(select(AppointmentAssignmentRequest).where(AppointmentAssignmentRequest.ticket_id == ticket_id))).scalars().all())


def test_assignment_notification_uses_outbox_and_requires_recipient_acknowledgement() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case())
        appointment = book(client, fixture).json()
        notification, outbox = asyncio.run(notification_outbox(appointment["id"]))
        assert outbox is not None
        assert outbox.status == "PENDING"
        assert json.loads(outbox.payload_json)["recipient_user_id"] == str(fixture["doctor"])
        assert PHONE not in outbox.payload_json

        use_session(client, fixture["doctor_tokens"])
        row = next(item for item in client.get("/api/v1/notifications").json() if item["id"] == str(notification.id))
        assert row["requires_acknowledgement"] is True
        acknowledged = client.patch(f"/api/v1/notifications/{notification.id}/acknowledge")
        assert acknowledged.status_code == 200
        assert acknowledged.json()["acknowledged_at"] is not None

        client.post("/api/v1/auth/logout")
        use_session(client, fixture["other_tokens"])
        assert client.patch(f"/api/v1/notifications/{notification.id}/acknowledge").status_code == 404


def test_assignment_requests_are_membership_scoped_and_minimal() -> None:
    with TestClient(app) as client:
        fixture = asyncio.run(seed_case(provider_has_doctor=False))
        assert book(client, fixture).status_code == 409
        requests = asyncio.run(assignment_requests(fixture["ticket"]))
        assert len(requests) == 1
        assert requests[0].recipient_user_id == fixture["doctor"]
        use_session(client, fixture["doctor_tokens"])
        rows = client.get("/api/v1/appointments/assignment-requests")
        assert rows.status_code == 200
        assert len(rows.json()) == 1
        serialized = json.dumps(rows.json())
        assert PHONE not in serialized
        assert "ticket_id" not in rows.json()[0]
        client.post("/api/v1/auth/logout")
        use_session(client, fixture["other_tokens"])
        assert client.get("/api/v1/appointments/assignment-requests").json() == []
