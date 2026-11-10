from __future__ import annotations

from fastapi import APIRouter

from app.routes.clinical_helpers import *  # noqa: F403
from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/appointments/slots", response_model=list[SlotResponse])
async def list_slots(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[SlotResponse]:
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    result = await session.execute(
        select(ProviderSlot, Provider)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(ProviderSlot.tenant_id == tenant_id, Provider.is_active.is_(True))
        .order_by(ProviderSlot.starts_at.asc())
    )
    return [
        SlotResponse(
            id=slot.id,
            tenant_id=slot.tenant_id,
            provider_name=provider.full_name,
            specialty=provider.specialty,
            room_label=provider.room_label,
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            is_locked=slot.is_locked,
            lock_reason=slot.lock_reason,
            is_booked=slot.is_booked,
        )
        for slot, provider in result.all()
    ]


@router.patch("/appointments/slots/{slot_id}/lock")
async def lock_slot(
    slot_id: str,
    payload: SlotLockRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    account = await require_roles(
        request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"}
    )
    slot = await session.scalar(
        select(ProviderSlot)
        .where(
            ProviderSlot.id == uuid.UUID(slot_id),
            ProviderSlot.tenant_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Appointment slot not found")
    if slot.is_booked and payload.is_locked:
        raise HTTPException(status_code=409, detail="Booked slots cannot be blocked")
    slot.is_locked = payload.is_locked
    slot.lock_reason = payload.reason if payload.is_locked else None
    await session.commit()
    await triage_manager.broadcast(
        str(account.tenant_id),
        {
            "type": "appointment.updated",
            "tenant_id": str(account.tenant_id),
            "payload": {
                "slot_id": slot_id,
                "is_locked": slot.is_locked,
                "lock_reason": slot.lock_reason,
            },
            "priority": "NORMAL",
        },
    )
    return {
        "ok": True,
        "slot_id": slot_id,
        "is_locked": slot.is_locked,
        "lock_reason": slot.lock_reason,
    }


@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
async def book_appointment(
    payload: AppointmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    authorization = request.headers.get("authorization", "")
    access_token = request.cookies.get(ACCESS_COOKIE) or (
        authorization[7:].strip()
        if authorization.lower().startswith("bearer ")
        else None
    )
    authenticated = (
        await account_for_access_token(session, access_token) if access_token else None
    )
    requester = authenticated[0] if authenticated else None
    owner_tenant_id = (
        requester.tenant_id
        if requester and requester.role == "patient"
        else uuid.UUID(public_tenant_id())
    )
    await apply_tenant_context(session, owner_tenant_id)
    ticket = await session.scalar(
        select(Ticket)
        .where(
            Ticket.id == payload.ticket_id,
            Ticket.customer_phone == payload.customer_phone,
        )
        .with_for_update()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found for this phone")
    destination_tenant_id = ticket_destination_id(ticket)
    specialty_id = ticket.assigned_specialty
    department_id = department_for_specialty(specialty_id)
    if not specialty_id:
        raise HTTPException(
            status_code=409,
            detail="Ticket has no triage specialty for doctor assignment",
        )
    existing = await session.scalar(
        select(Appointment).where(
            Appointment.ticket_id == ticket.id, Appointment.status == "BOOKED"
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ticket already has an appointment")

    await apply_tenant_context(session, destination_tenant_id)
    row = (
        await session.execute(
            select(ProviderSlot, Provider, AuthAccount, StaffMembership)
            .join(Provider, Provider.id == ProviderSlot.provider_id)
            .join(AuthAccount, AuthAccount.id == Provider.doctor_id)
            .join(
                StaffMembership,
                (StaffMembership.hospital_id == ProviderSlot.tenant_id)
                & (StaffMembership.user_id == AuthAccount.id)
                & (StaffMembership.specialty_id == Provider.specialty),
            )
            .where(
                ProviderSlot.id == payload.slot_id,
                ProviderSlot.tenant_id == destination_tenant_id,
                ProviderSlot.is_locked.is_(False),
                ProviderSlot.is_booked.is_(False),
                Provider.is_active.is_(True),
                Provider.specialty == specialty_id,
                AuthAccount.is_active.is_(True),
                AuthAccount.role.in_(["doctor", "specialist"]),
                StaffMembership.department_id == department_id,
                StaffMembership.role.in_(["doctor", "specialist"]),
                StaffMembership.is_active.is_(True),
                StaffMembership.is_on_duty.is_(True),
                StaffMembership.verification_status == "VERIFIED",
                StaffMembership.employment_status == "ACTIVE",
                StaffMembership.active_from <= ProviderSlot.starts_at,
                or_(
                    StaffMembership.active_until.is_(None),
                    StaffMembership.active_until >= ProviderSlot.starts_at,
                ),
            )
            .order_by(ProviderSlot.starts_at.asc(), Provider.full_name.asc())
            .with_for_update()
        )
    ).first()
    if not row:
        ticket.queue_status = "AWAITING_CLINICAL_REVIEW"
        eligible_rows = list(
            (
                await session.execute(
                    select(AuthAccount, StaffMembership)
                    .join(StaffMembership, StaffMembership.user_id == AuthAccount.id)
                    .where(
                        StaffMembership.hospital_id == destination_tenant_id,
                        StaffMembership.department_id == department_id,
                        StaffMembership.specialty_id == specialty_id,
                        StaffMembership.role.in_(
                            ["doctor", "specialist", "department_coordinator"]
                        ),
                        StaffMembership.is_active.is_(True),
                        StaffMembership.is_on_duty.is_(True),
                        StaffMembership.verification_status == "VERIFIED",
                        StaffMembership.employment_status == "ACTIVE",
                        AuthAccount.is_active.is_(True),
                    )
                )
            ).all()
        )
        recipients = eligible_rows or [(None, None)]
        for recipient, recipient_membership in recipients:
            session.add(
                AppointmentAssignmentRequest(
                    hospital_id=destination_tenant_id,
                    department_id=department_id,
                    ticket_id=ticket.id,
                    recipient_user_id=recipient.id if recipient else None,
                    recipient_membership_id=(
                        recipient_membership.id if recipient_membership else None
                    ),
                    specialty_id=specialty_id,
                    status="OPEN",
                    expires_at=utc_now() + timedelta(minutes=15),
                )
            )
            await create_appointment_notification(
                session,
                tenant_id=destination_tenant_id,
                recipient_account_id=recipient.id if recipient else None,
                recipient_role=(
                    recipient_membership.role
                    if recipient_membership
                    else "department_coordinator"
                ),
                appointment=None,
                ticket=ticket,
                event_type="APPOINTMENT_ASSIGNMENT_REQUESTED",
                title="Specialist review needed",
                body="No eligible verified on-duty clinician was available for the routed appointment slot.",
                payload={
                    "ticket_id": str(ticket.id),
                    "specialty_id": specialty_id,
                    "hospital_id": str(destination_tenant_id),
                    "department_id": department_id,
                },
                recipient_membership_id=(
                    recipient_membership.id if recipient_membership else None
                ),
                hospital_id=destination_tenant_id,
                department_id=department_id,
            )
        await session.commit()
        await broadcast_appointment_event(
            destination_tenant_id,
            "APPOINTMENT_ASSIGNMENT_REQUESTED",
            {
                "ticket_id": str(ticket.id),
                "specialty_id": specialty_id,
                "department_id": department_id,
            },
        )
        raise HTTPException(
            status_code=409,
            detail="No eligible verified on-duty clinician is available in the routed hospital department for this specialty and slot",
        )
    slot, provider, doctor, membership = row
    day_start = datetime.combine(
        slot.starts_at.date(), time.min, tzinfo=slot.starts_at.tzinfo or UTC
    )
    day_end = day_start + timedelta(days=1)
    booked_count = await session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.hospital_id == destination_tenant_id,
            Appointment.doctor_id == doctor.id,
            Appointment.status == "BOOKED",
            Appointment.starts_at >= day_start,
            Appointment.starts_at < day_end,
        )
    )
    if (booked_count or 0) >= provider.max_daily_capacity:
        ticket.queue_status = "AWAITING_CLINICAL_REVIEW"
        await create_appointment_notification(
            session,
            tenant_id=destination_tenant_id,
            recipient_account_id=None,
            recipient_role="department_coordinator",
            appointment=None,
            ticket=ticket,
            event_type="appointment.reassignment_requested",
            title="Doctor capacity reached",
            body="The eligible doctor for this routed appointment has reached capacity.",
            payload={
                "ticket_id": str(ticket.id),
                "doctor_id": str(doctor.id),
                "specialty_id": specialty_id,
            },
        )
        await session.commit()
        await broadcast_appointment_event(
            destination_tenant_id,
            "appointment.reassignment_requested",
            {
                "ticket_id": str(ticket.id),
                "doctor_id": str(doctor.id),
                "specialty_id": specialty_id,
                "department_id": department_id,
            },
        )
        raise HTTPException(
            status_code=409,
            detail="Eligible doctor capacity has been reached at the routed hospital",
        )

    slot.is_booked = True
    ticket.appointment_slot = slot.starts_at
    ticket.assigned_specialist_id = doctor.id
    appointment = Appointment(
        tenant_id=destination_tenant_id,
        hospital_id=destination_tenant_id,
        department_id=department_id,
        ticket_id=ticket.id,
        doctor_id=doctor.id,
        staff_membership_id=membership.id,
        specialty_id=membership.specialty_id,
        slot_id=slot.id,
        customer_phone=payload.customer_phone,
        urgency=ticket.urgency_level,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        status="BOOKED",
    )
    session.add(appointment)
    await session.flush()
    patient_account = (
        requester
        if requester and requester.role == "patient"
        else await session.scalar(
            select(AuthAccount).where(
                AuthAccount.role == "patient",
                AuthAccount.phone == ticket.customer_phone,
            )
        )
    )
    patient_display_name = (
        f"{patient_account.first_name} {patient_account.last_name}".strip()
        if patient_account
        else "Patient"
    )
    response_payload = {
        "appointment_id": str(appointment.id),
        "ticket_id": str(ticket.id),
        "patient_phone": ticket.customer_phone,
        "patient_display_name": patient_display_name,
        "starts_at": slot.starts_at.isoformat(),
        "ends_at": slot.ends_at.isoformat(),
        "hospital_id": str(destination_tenant_id),
        "department_id": department_id,
        "doctor_id": str(doctor.id),
        "staff_membership_id": str(membership.id),
        "specialty_id": membership.specialty_id,
        "urgency": ticket.urgency_level,
        "room_label": provider.room_label,
        "actions": ["view", "accept", "request_reassignment"],
    }
    doctor_notification = await create_appointment_notification(
        session,
        tenant_id=destination_tenant_id,
        recipient_account_id=doctor.id,
        recipient_role="doctor",
        appointment=appointment,
        ticket=ticket,
        event_type="APPOINTMENT_ASSIGNED",
        title="New appointment assigned",
        body=f"Patient: {patient_display_name}. Date: {slot.starts_at:%d %B %Y}. Time: {slot.starts_at:%I:%M %p}. Department: {department_id}. Urgency: {ticket.urgency_level}. Room: {provider.room_label}.",
        payload=response_payload,
        recipient_membership_id=membership.id,
        hospital_id=destination_tenant_id,
        department_id=department_id,
    )
    await create_appointment_notification(
        session,
        tenant_id=ticket.tenant_id,
        recipient_account_id=patient_account.id if patient_account else None,
        recipient_role="patient",
        appointment=appointment,
        ticket=ticket,
        event_type="appointment.created",
        title="Appointment confirmed",
        body="Your appointment has been confirmed at the routed hospital.",
        payload=response_payload,
    )
    await write_audit_log(
        session,
        AuditAction.APPOINTMENT_BOOKED,
        actor_id=None,
        actor_type="PATIENT",
        tenant_id=str(destination_tenant_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Appointment",
        resource_id=str(appointment.id),
    )
    await session.commit()
    await apply_tenant_context(session, destination_tenant_id)
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(
        destination_tenant_id,
        "APPOINTMENT_ASSIGNED",
        response_payload,
        doctor.id,
        session=session,
        notification_id=doctor_notification.id,
    )
    await broadcast_appointment_event(
        ticket.tenant_id,
        "appointment.created",
        response_payload,
        patient_account.id if patient_account else None,
    )
    return response


@router.get("/appointments", response_model=list[AppointmentResponse])
async def staff_appointments(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[AppointmentResponse]:
    account = await require_roles(
        request,
        session,
        {
            "specialist",
            "doctor",
            "nurse",
            "hospital_admin",
            "department_coordinator",
            "admin",
        },
    )
    memberships = await active_staff_memberships(session, account)
    membership_ids = [membership.id for membership in memberships]
    workspace_pairs = {
        (membership.hospital_id, membership.department_id) for membership in memberships
    }
    if account.role in {"doctor", "specialist"}:
        query = select(Appointment).where(
            Appointment.hospital_id.in_(
                [hospital_id for hospital_id, _department_id in workspace_pairs]
                or [account.tenant_id]
            ),
            or_(
                Appointment.doctor_id == account.id,
                (
                    Appointment.staff_membership_id.in_(membership_ids)
                    if membership_ids
                    else False
                ),
            ),
        )
    elif account.role == "nurse":
        if not workspace_pairs:
            raise HTTPException(
                status_code=403, detail="No verified active nurse workspace"
            )
        query = select(Appointment).where(
            or_(
                *[
                    Appointment.hospital_id == hospital_id
                    for hospital_id, _department_id in workspace_pairs
                ]
            ),
            or_(
                *[
                    Appointment.department_id == department_id
                    for _hospital_id, department_id in workspace_pairs
                ]
            ),
            Appointment.status == "BOOKED",
        )
    elif account.role == "department_coordinator":
        if not workspace_pairs:
            raise HTTPException(
                status_code=403, detail="No verified active coordinator workspace"
            )
        query = select(Appointment).where(
            or_(
                *[
                    Appointment.hospital_id == hospital_id
                    for hospital_id, _department_id in workspace_pairs
                ]
            ),
            or_(
                *[
                    Appointment.department_id == department_id
                    for _hospital_id, department_id in workspace_pairs
                ]
            ),
        )
    else:
        query = select(Appointment).where(Appointment.hospital_id == account.tenant_id)
    result = await session.execute(query.order_by(Appointment.created_at.asc()))
    return [
        await appointment_response(session, appointment)
        for appointment in result.scalars().all()
    ]


@router.get("/patient/appointments", response_model=list[AppointmentResponse])
async def patient_appointments(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[AppointmentResponse]:
    account = await require_account(request, session)
    if account.role != "patient" or not account.phone:
        raise HTTPException(status_code=403, detail="Patient access required")
    ticket_rows = list(
        (
            await session.execute(
                select(Ticket)
                .where(Ticket.customer_phone == account.phone)
                .order_by(Ticket.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    ticket_ids = [ticket.id for ticket in ticket_rows]
    if not ticket_ids:
        return []
    appointments: list[Appointment] = []
    destination_ids = {ticket_destination_id(ticket) for ticket in ticket_rows}
    for destination_id in destination_ids:
        await apply_tenant_context(session, destination_id)
        result = await session.execute(
            select(Appointment)
            .where(
                Appointment.customer_phone == account.phone,
                Appointment.ticket_id.in_(ticket_ids),
            )
            .order_by(Appointment.created_at.desc())
        )
        appointments.extend(result.scalars().all())
    appointments.sort(key=lambda appointment: appointment.created_at, reverse=True)
    return [
        await appointment_response(session, appointment) for appointment in appointments
    ]


@router.patch(
    "/appointments/{appointment_id}/cancel", response_model=AppointmentResponse
)
async def cancel_appointment(
    appointment_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> AppointmentResponse:
    account = await require_account(request, session)
    appointment_query = select(Appointment).where(
        Appointment.id == uuid.UUID(appointment_id)
    )
    if account.role == "patient":
        appointment_query = appointment_query.where(
            Appointment.customer_phone == account.phone
        )
    else:
        appointment_query = appointment_query.where(
            Appointment.hospital_id == account.tenant_id
        )
        if account.role in {"doctor", "specialist"}:
            appointment_query = appointment_query.where(
                Appointment.doctor_id == account.id
            )
    appointment = await session.scalar(appointment_query.with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != "BOOKED":
        raise HTTPException(status_code=409, detail="Appointment is not active")
    slot = await session.scalar(
        select(ProviderSlot)
        .where(ProviderSlot.id == appointment.slot_id)
        .with_for_update()
    )
    appointment.status = "CANCELLED"
    appointment.updated_at = utc_now()
    if slot:
        slot.is_booked = False
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = None
        await create_appointment_notification(
            session,
            tenant_id=appointment.hospital_id,
            recipient_account_id=appointment.doctor_id,
            recipient_role="doctor",
            appointment=appointment,
            ticket=ticket,
            event_type="APPOINTMENT_CANCELLED",
            title="Appointment cancelled",
            body="An assigned appointment was cancelled.",
            payload={
                "appointment_id": str(appointment.id),
                "ticket_id": str(ticket.id),
            },
            recipient_membership_id=appointment.staff_membership_id,
            hospital_id=appointment.hospital_id,
            department_id=appointment.department_id,
        )
        patient_account = await session.scalar(
            select(AuthAccount).where(
                AuthAccount.role == "patient",
                AuthAccount.phone == ticket.customer_phone,
            )
        )
        if patient_account:
            await create_appointment_notification(
                session,
                tenant_id=ticket.tenant_id,
                recipient_account_id=patient_account.id,
                recipient_role="patient",
                appointment=appointment,
                ticket=ticket,
                event_type="APPOINTMENT_CANCELLED",
                title="Appointment cancelled",
                body="Your appointment has been cancelled.",
                payload={
                    "appointment_id": str(appointment.id),
                    "ticket_id": str(ticket.id),
                },
            )
    await write_audit_log(
        session,
        AuditAction.APPOINTMENT_CANCELLED,
        actor_id=str(account.id),
        actor_type=account.role.upper(),
        tenant_id=str(appointment.hospital_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Appointment",
        resource_id=str(appointment.id),
    )
    await session.commit()
    await apply_tenant_context(session, appointment.hospital_id)
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(
        appointment.hospital_id,
        "appointment.cancelled",
        response.model_dump(),
        appointment.doctor_id,
    )
    return response


@router.patch(
    "/appointments/{appointment_id}/reschedule", response_model=AppointmentResponse
)
async def reschedule_appointment(
    appointment_id: str,
    payload: AppointmentMoveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> AppointmentResponse:
    account = await require_account(request, session)
    appointment_query = select(Appointment).where(
        Appointment.id == uuid.UUID(appointment_id)
    )
    if account.role == "patient":
        appointment_query = appointment_query.where(
            Appointment.customer_phone == account.phone
        )
    else:
        appointment_query = appointment_query.where(
            Appointment.hospital_id == account.tenant_id
        )
        if account.role in {"doctor", "specialist"}:
            appointment_query = appointment_query.where(
                Appointment.doctor_id == account.id
            )
    appointment = await session.scalar(appointment_query.with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != "BOOKED":
        raise HTTPException(status_code=409, detail="Appointment is not active")
    slots = (
        (
            await session.execute(
                select(ProviderSlot)
                .where(ProviderSlot.id.in_([appointment.slot_id, payload.slot_id]))
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    slot_map = {slot.id: slot for slot in slots}
    old_slot, new_slot = slot_map.get(appointment.slot_id), slot_map.get(
        payload.slot_id
    )
    if not new_slot or new_slot.tenant_id != appointment.hospital_id:
        raise HTTPException(status_code=404, detail="New slot not found")
    provider = await session.scalar(
        select(Provider).where(Provider.id == new_slot.provider_id)
    )
    if (
        not provider
        or provider.doctor_id != appointment.doctor_id
        or provider.specialty != appointment.specialty_id
    ):
        raise HTTPException(
            status_code=409,
            detail="New slot does not match the assigned doctor and specialty",
        )
    if new_slot.is_locked or new_slot.is_booked:
        raise HTTPException(status_code=409, detail="New slot is no longer available")
    if old_slot:
        old_slot.is_booked = False
    new_slot.is_booked = True
    appointment.slot_id = new_slot.id
    appointment.starts_at = new_slot.starts_at
    appointment.ends_at = new_slot.ends_at
    appointment.updated_at = utc_now()
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = new_slot.starts_at
        await create_appointment_notification(
            session,
            tenant_id=appointment.hospital_id,
            recipient_account_id=appointment.doctor_id,
            recipient_role="doctor",
            appointment=appointment,
            ticket=ticket,
            event_type="APPOINTMENT_RESCHEDULED",
            title="Appointment rescheduled",
            body="An assigned appointment was rescheduled.",
            payload={
                "appointment_id": str(appointment.id),
                "ticket_id": str(ticket.id),
                "starts_at": new_slot.starts_at.isoformat(),
            },
            recipient_membership_id=appointment.staff_membership_id,
            hospital_id=appointment.hospital_id,
            department_id=appointment.department_id,
        )
        patient_account = await session.scalar(
            select(AuthAccount).where(
                AuthAccount.role == "patient",
                AuthAccount.phone == ticket.customer_phone,
            )
        )
        if patient_account:
            await create_appointment_notification(
                session,
                tenant_id=ticket.tenant_id,
                recipient_account_id=patient_account.id,
                recipient_role="patient",
                appointment=appointment,
                ticket=ticket,
                event_type="APPOINTMENT_RESCHEDULED",
                title="Appointment rescheduled",
                body=f"Your appointment was moved to {new_slot.starts_at:%d %B %Y at %I:%M %p}.",
                payload={
                    "appointment_id": str(appointment.id),
                    "ticket_id": str(ticket.id),
                    "starts_at": new_slot.starts_at.isoformat(),
                },
            )
    await write_audit_log(
        session,
        AuditAction.APPOINTMENT_RESCHEDULED,
        actor_id=str(account.id),
        actor_type=account.role.upper(),
        tenant_id=str(appointment.hospital_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Appointment",
        resource_id=str(appointment.id),
        metadata={"new_slot_id": str(new_slot.id)},
    )
    await session.commit()
    await apply_tenant_context(session, appointment.hospital_id)
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(
        appointment.hospital_id,
        "appointment.rescheduled",
        response.model_dump(),
        appointment.doctor_id,
    )
    return response


@router.post(
    "/appointments/{appointment_id}/accept", response_model=AppointmentResponse
)
async def accept_unassigned_appointment(
    appointment_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> AppointmentResponse:
    account = await require_roles(request, session, {"doctor", "specialist"})
    appointment = await session.scalar(
        select(Appointment)
        .where(
            Appointment.id == uuid.UUID(appointment_id),
            Appointment.hospital_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.doctor_id is not None:
        raise HTTPException(
            status_code=409, detail="Appointment has already been accepted"
        )
    if appointment.status not in {"AWAITING_CLINICAL_REVIEW", "SPECIALIST_UNAVAILABLE"}:
        raise HTTPException(
            status_code=409, detail="Appointment is not awaiting doctor acceptance"
        )
    slot, provider = (
        await session.execute(
            select(ProviderSlot, Provider)
            .join(Provider, Provider.id == ProviderSlot.provider_id)
            .where(
                ProviderSlot.id == appointment.slot_id,
                ProviderSlot.tenant_id == appointment.hospital_id,
            )
            .with_for_update()
        )
    ).one()
    membership = await session.scalar(
        select(StaffMembership).where(
            StaffMembership.hospital_id == appointment.hospital_id,
            StaffMembership.department_id == appointment.department_id,
            StaffMembership.user_id == account.id,
            StaffMembership.role.in_(["doctor", "specialist"]),
            StaffMembership.specialty_id == appointment.specialty_id,
            StaffMembership.is_active.is_(True),
            StaffMembership.is_on_duty.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
        )
    )
    if (
        not membership
        or not account.is_active
        or provider.specialty != appointment.specialty_id
        or slot.is_locked
        or slot.is_booked
    ):
        raise HTTPException(
            status_code=403, detail="Doctor is not eligible to accept this appointment"
        )
    appointment.doctor_id = account.id
    appointment.staff_membership_id = membership.id
    appointment.status = "BOOKED"
    slot.is_booked = True
    competing_requests = list(
        (
            await session.execute(
                select(AppointmentAssignmentRequest)
                .where(
                    AppointmentAssignmentRequest.ticket_id == appointment.ticket_id,
                    AppointmentAssignmentRequest.status == "OPEN",
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for assignment_request in competing_requests:
        assignment_request.appointment_id = appointment.id
        assignment_request.status = (
            "ACCEPTED"
            if assignment_request.recipient_user_id == account.id
            else "CLOSED"
        )
        assignment_request.accepted_at = (
            utc_now() if assignment_request.recipient_user_id == account.id else None
        )
        assignment_request.closed_at = utc_now()
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = appointment.starts_at or slot.starts_at
        doctor_notification = await create_appointment_notification(
            session,
            tenant_id=appointment.hospital_id,
            recipient_account_id=account.id,
            recipient_role="doctor",
            appointment=appointment,
            ticket=ticket,
            event_type="APPOINTMENT_ASSIGNED",
            title="New appointment assigned",
            body="This appointment is now assigned to you.",
            payload={
                "appointment_id": str(appointment.id),
                "ticket_id": str(ticket.id),
                "department_id": appointment.department_id,
                "specialty_id": appointment.specialty_id,
            },
            recipient_membership_id=membership.id,
            hospital_id=appointment.hospital_id,
            department_id=appointment.department_id,
        )
        patient_account = await session.scalar(
            select(AuthAccount).where(
                AuthAccount.role == "patient",
                AuthAccount.phone == ticket.customer_phone,
            )
        )
        if patient_account:
            await create_appointment_notification(
                session,
                tenant_id=ticket.tenant_id,
                recipient_account_id=patient_account.id,
                recipient_role="patient",
                appointment=appointment,
                ticket=ticket,
                event_type="APPOINTMENT_ASSIGNED",
                title="Appointment confirmed",
                body="A clinician has accepted your appointment.",
                payload={
                    "appointment_id": str(appointment.id),
                    "ticket_id": str(ticket.id),
                },
            )
    await session.commit()
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(
        appointment.hospital_id,
        "APPOINTMENT_ASSIGNED",
        response.model_dump(),
        account.id,
        session=session,
        notification_id=doctor_notification.id,
    )
    return response


@router.get("/appointments/assignment-requests")
async def list_assignment_requests(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_roles(
        request, session, {"doctor", "specialist", "department_coordinator"}
    )
    memberships = await active_staff_memberships(session, account)
    membership_ids = [membership.id for membership in memberships]
    if not membership_ids:
        return []
    now = utc_now()
    requests = list(
        (
            await session.execute(
                select(AppointmentAssignmentRequest)
                .where(
                    AppointmentAssignmentRequest.recipient_user_id == account.id,
                    AppointmentAssignmentRequest.recipient_membership_id.in_(
                        membership_ids
                    ),
                    AppointmentAssignmentRequest.status == "OPEN",
                    AppointmentAssignmentRequest.expires_at > now,
                )
                .order_by(AppointmentAssignmentRequest.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(assignment_request.id),
            "hospital_id": str(assignment_request.hospital_id),
            "department_id": assignment_request.department_id,
            "specialty_id": assignment_request.specialty_id,
            "status": assignment_request.status,
            "expires_at": assignment_request.expires_at,
            "created_at": assignment_request.created_at,
        }
        for assignment_request in requests
    ]


@router.post("/appointments/{appointment_id}/encounter", status_code=201)
async def start_appointment_encounter(
    appointment_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    membership = await verified_membership(session, account)
    appointment = await session.scalar(
        select(Appointment).where(
            Appointment.id == parse_uuid(appointment_id, "appointment_id"),
            Appointment.hospital_id == membership.hospital_id,
            Appointment.doctor_id == account.id,
            Appointment.status == "BOOKED",
        )
    )
    if not appointment:
        raise HTTPException(
            status_code=404, detail="Assigned booked appointment not found"
        )
    existing = await session.scalar(
        select(Encounter)
        .where(Encounter.appointment_id == appointment.id)
        .order_by(Encounter.started_at.desc())
    )
    if existing:
        return {
            "id": str(existing.id),
            "patient_id": str(existing.patient_id),
            "status": existing.status,
            "started_at": existing.started_at,
        }
    patient_id = await session.scalar(
        select(AuthAccount.id).where(
            AuthAccount.role == "patient",
            AuthAccount.phone == appointment.customer_phone,
        )
    )
    encounter = Encounter(
        patient_id=patient_id,
        facility_id=appointment.hospital_id,
        appointment_id=appointment.id,
        assigned_clinician_id=account.id,
        encounter_type="APPOINTMENT",
    )
    if not encounter.patient_id:
        raise HTTPException(
            status_code=404, detail="Appointment patient account not found"
        )
    session.add(encounter)
    await session.flush()
    await audit(
        session,
        request,
        account,
        "Encounter",
        encounter.id,
        "STARTED",
        appointment.hospital_id,
    )
    await session.commit()
    return {
        "id": str(encounter.id),
        "patient_id": str(encounter.patient_id),
        "status": encounter.status,
        "started_at": encounter.started_at,
    }
