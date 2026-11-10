from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403
from app.routes.tickets.queue import escalate_ticket

router = APIRouter(prefix="/api/v1")


@router.get("/clinician/patients/{ticket_id}/record")
async def clinician_patient_record(
    ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, membership, ticket, appointment, care_assignment, break_glass = (
        await clinician_record_context(session, request, ticket_id)
    )
    role_sections = (
        NURSE_RECORD_SECTIONS if account.role == "nurse" else DOCTOR_RECORD_SECTIONS
    )
    assignment_sections = (
        set(json.loads(care_assignment.permitted_sections_json))
        if care_assignment and care_assignment.permitted_sections_json
        else role_sections
    )
    permitted = (
        role_sections & assignment_sections if care_assignment else role_sections
    )
    requested_param = str(request.query_params.get("sections") or "").strip()
    requested = (
        {item.strip() for item in requested_param.split(",") if item.strip()}
        if requested_param
        else permitted
    )
    if not requested <= permitted:
        await record_access_audit(
            session,
            request,
            account,
            membership,
            ticket,
            outcome="DENIED",
            sections=requested,
            reason="SECTION_NOT_PERMITTED",
            appointment_id=appointment.id if appointment else None,
            break_glass=break_glass,
        )
        await session.commit()
        raise HTTPException(
            status_code=403,
            detail="One or more requested record sections are not permitted",
        )
    patient = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone
        )
    )
    notes = (
        list(
            (
                await session.execute(
                    select(ConsultationNote)
                    .where(ConsultationNote.ticket_id == ticket.id)
                    .order_by(ConsultationNote.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        if "clinical_notes" in requested
        else []
    )
    appointments = (
        list(
            (
                await session.execute(
                    select(Appointment)
                    .where(Appointment.ticket_id == ticket.id)
                    .order_by(Appointment.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        if "appointments" in requested
        else []
    )
    values: dict[str, Any] = {
        "identity": {
            "id": str(patient.id) if patient else None,
            "first_name": patient.first_name if patient else None,
            "last_name": patient.last_name if patient else None,
            "card_number": patient.card_number if patient else None,
        },
        "triage": {
            "ticket_id": str(ticket.id),
            "symptoms": ticket.raw_intake_text,
            "condition": ticket.matched_condition_id,
            "urgency": ticket.urgency_level,
            "specialty": ticket.assigned_specialty,
        },
        "allergies": patient.known_allergies if patient else None,
        "current_medications": patient.current_medications if patient else None,
        "existing_conditions": [],
        "diagnoses": [],
        "laboratory_results": [],
        "imaging_results": [],
        "prescriptions": [],
        "care_plans": [],
        "referrals": [],
        "safety_warnings": [],
        "appointments": [
            {
                "id": str(item.id),
                "status": item.status,
                "starts_at": item.starts_at,
                "department_id": item.department_id,
                "specialty_id": item.specialty_id,
            }
            for item in appointments
        ],
        "clinical_notes": [
            {"id": str(note.id), "body": note.body, "created_at": note.created_at}
            for note in notes
        ],
        "hmo": {"provider": patient.hmo_provider if patient else None},
        "emergency_contact": patient.emergency_contact if patient else None,
    }
    await record_access_audit(
        session,
        request,
        account,
        membership,
        ticket,
        outcome="ALLOWED",
        sections=requested,
        reason="BREAK_GLASS" if break_glass else "ACTIVE_TREATMENT",
        appointment_id=appointment.id if appointment else None,
        break_glass=break_glass,
    )
    await session.commit()
    return {
        "patient_id": str(patient.id) if patient else None,
        "ticket_id": str(ticket.id),
        "hospital_id": str(ticket_destination_id(ticket)),
        "department_id": membership.department_id,
        "relationship": "BREAK_GLASS" if break_glass else "ACTIVE_TREATMENT",
        "sections": {section: values[section] for section in sorted(requested)},
    }


@router.post("/clinician/patients/{ticket_id}/break-glass", status_code=201)
async def create_break_glass_access(
    ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse"})
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 10 or payload.get("confirmed") is not True:
        raise HTTPException(
            status_code=422,
            detail="A specific emergency reason and explicit confirmation are required",
        )
    ticket = None
    membership = None
    for candidate in await active_staff_memberships(session, account):
        await apply_tenant_context(session, candidate.hospital_id)
        candidate_ticket = await session.scalar(
            select(Ticket).where(
                Ticket.id == ticket_id, ticket_visible_to_tenant(candidate.hospital_id)
            )
        )
        if (
            candidate_ticket
            and ticket_destination_id(candidate_ticket) == candidate.hospital_id
        ):
            ticket, membership = candidate_ticket, candidate
            break
    if not ticket or not membership:
        await write_audit_log(
            session,
            AuditAction.PATIENT_RECORD_VIEWED,
            actor_id=str(account.id),
            actor_type=account.role.upper(),
            tenant_id=str(account.tenant_id),
            ip_address=request.client.host if request.client else "127.0.0.1",
            resource_type="PatientRecord",
            resource_id=str(ticket_id),
            metadata={
                "outcome": "DENIED",
                "access_reason": "BREAK_GLASS_NO_ACTIVE_MEMBERSHIP",
                "record_sections_viewed": [],
                "break_glass_used": True,
            },
        )
        await session.commit()
        raise HTTPException(
            status_code=403,
            detail="Break-glass requires active membership at the routed hospital",
        )
    hospital_id = ticket_destination_id(ticket)
    if not membership:
        await record_access_audit(
            session,
            request,
            account,
            None,
            ticket,
            outcome="DENIED",
            sections=set(),
            reason="BREAK_GLASS_NO_ACTIVE_MEMBERSHIP",
            break_glass=True,
        )
        await session.commit()
        raise HTTPException(
            status_code=403,
            detail="Break-glass requires active membership at the routed hospital",
        )
    grant = BreakGlassGrant(
        hospital_id=hospital_id,
        ticket_id=ticket.id,
        user_id=account.id,
        membership_id=membership.id,
        reason=reason,
        confirmed=True,
        expires_at=utc_now() + timedelta(minutes=30),
    )
    session.add(grant)
    await session.flush()
    await record_access_audit(
        session,
        request,
        account,
        membership,
        ticket,
        outcome="ALLOWED",
        sections=set(),
        reason=reason,
        break_glass=True,
    )
    compliance_rows = (
        await session.execute(
            select(AuthAccount, StaffMembership)
            .join(StaffMembership, StaffMembership.user_id == AuthAccount.id)
            .where(
                StaffMembership.hospital_id == hospital_id,
                StaffMembership.role.in_(["hospital_admin", "department_coordinator"]),
                StaffMembership.is_active.is_(True),
                StaffMembership.verification_status == "VERIFIED",
                StaffMembership.employment_status == "ACTIVE",
            )
        )
    ).all()
    for recipient, recipient_membership in compliance_rows:
        await create_appointment_notification(
            session,
            tenant_id=hospital_id,
            recipient_account_id=recipient.id,
            recipient_role=recipient_membership.role,
            appointment=None,
            ticket=ticket,
            event_type="BREAK_GLASS_REVIEW_REQUIRED",
            title="Emergency patient-record access",
            body="A clinician used emergency access. Compliance review is required.",
            payload={
                "grant_id": str(grant.id),
                "ticket_id": str(ticket.id),
                "clinician_id": str(account.id),
            },
            recipient_membership_id=recipient_membership.id,
            hospital_id=hospital_id,
            department_id=membership.department_id,
            priority="HIGH",
        )
    patient = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone
        )
    )
    if patient:
        await create_appointment_notification(
            session,
            tenant_id=ticket.tenant_id,
            recipient_account_id=patient.id,
            recipient_role="patient",
            appointment=None,
            ticket=ticket,
            event_type="PATIENT_RECORD_EMERGENCY_ACCESS",
            title="Emergency record access",
            body="Your record was accessed for immediate emergency care.",
            payload={"ticket_id": str(ticket.id), "grant_id": str(grant.id)},
            priority="HIGH",
        )
    await session.commit()
    return {
        "id": str(grant.id),
        "status": "ACTIVE",
        "expires_at": grant.expires_at,
        "review_required": True,
    }


@router.get("/specialist/{resource}")
async def specialist_resource(
    resource: str,
    request: Request,
    assigned_only: bool = False,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if resource not in SPECIALIST_RESOURCES:
        raise HTTPException(status_code=404, detail="Specialist resource not found")
    account, membership = await require_specialist_workspace(request, session)
    hospital_id = membership.hospital_id
    ticket_query = select(Ticket).where(
        ticket_destination_queue(hospital_id),
        Ticket.assigned_specialist_id == account.id,
    )
    if assigned_only:
        ticket_query = ticket_query.where(Ticket.assigned_specialist_id == account.id)
    tickets = list(
        (await session.execute(ticket_query.order_by(Ticket.created_at.desc())))
        .scalars()
        .all()
    )
    providers = list(
        (
            await session.execute(
                select(Provider).where(
                    Provider.tenant_id == hospital_id, Provider.doctor_id == account.id
                )
            )
        )
        .scalars()
        .all()
    )
    provider_ids = [provider.id for provider in providers]
    appointment_rows = list(
        (
            await session.execute(
                select(Appointment, ProviderSlot, Provider)
                .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id)
                .join(Provider, Provider.id == ProviderSlot.provider_id)
                .where(
                    Appointment.hospital_id == hospital_id,
                    Appointment.doctor_id == account.id,
                    Appointment.staff_membership_id == membership.id,
                    ProviderSlot.provider_id.in_(provider_ids or [uuid.uuid4()]),
                )
                .order_by(ProviderSlot.starts_at)
            )
        ).all()
    )
    identity = {
        "name": f"Dr. {account.first_name} {account.last_name}",
        "specialty": account.specialty,
        "initials": f"{account.first_name[:1]}{account.last_name[:1]}",
    }
    patient_items = [
        {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "summary": ticket.raw_intake_text,
            "symptom_description": ticket.raw_intake_text,
            "matched_condition_name": (ticket.matched_condition_id or "Unclassified")
            .replace("_", " ")
            .title(),
            "assigned_specialty": ticket.assigned_specialty,
            "specialty": ticket.assigned_specialty,
            "urgency_level": ticket.urgency_level,
            "queue_status": ticket.queue_status,
            "status": (
                "ASSIGNED"
                if ticket.assigned_specialist_id == account.id
                else "UNASSIGNED"
            ),
            "assigned_to_me": ticket.assigned_specialist_id == account.id,
            "created_at": ticket.created_at.isoformat(),
        }
        for ticket in tickets
    ]
    appointment_items = [
        {
            "id": str(appointment.id),
            "ticket_id": str(appointment.ticket_id),
            "title": f"{appointment.customer_phone} · {provider.full_name}",
            "specialty": provider.specialty,
            "status": appointment.status,
            "scheduled_at": slot.starts_at.isoformat(),
            "subtitle": provider.room_label,
        }
        for appointment, slot, provider in appointment_rows
    ]
    if resource == "dashboard":
        assigned = [
            ticket for ticket in tickets if ticket.assigned_specialist_id == account.id
        ]
        return {
            "identity": identity,
            "stats": [
                {"title": "Assigned patients", "value": len(assigned), "tone": "sky"},
                {
                    "title": "Being seen",
                    "value": sum(
                        ticket.queue_status == "BEING_SEEN" for ticket in assigned
                    ),
                    "tone": "amber",
                },
                {
                    "title": "Appointments",
                    "value": sum(
                        item["status"] == "BOOKED" for item in appointment_items
                    ),
                    "tone": "violet",
                },
                {
                    "title": "Critical",
                    "value": sum(
                        ticket.urgency_level == "CRITICAL" for ticket in assigned
                    ),
                    "tone": "rose",
                },
            ],
            "activity": patient_items[:8],
        }
    if resource in {"queue", "patients"}:
        return {"identity": identity, "items": patient_items}
    if resource == "appointments":
        return {"identity": identity, "items": appointment_items}
    if resource == "schedule":
        slots = list(
            (
                await session.execute(
                    select(ProviderSlot, Provider)
                    .join(Provider, Provider.id == ProviderSlot.provider_id)
                    .where(ProviderSlot.provider_id.in_(provider_ids or [uuid.uuid4()]))
                    .order_by(ProviderSlot.starts_at)
                )
            ).all()
        )
        return {
            "identity": identity,
            "items": [
                {
                    "id": str(slot.id),
                    "title": provider.full_name,
                    "scheduled_at": slot.starts_at.isoformat(),
                    "status": (
                        "BOOKED"
                        if slot.is_booked
                        else "LOCKED" if slot.is_locked else "AVAILABLE"
                    ),
                    "subtitle": provider.room_label,
                }
                for slot, provider in slots
            ],
        }
    if resource == "notes":
        notes = list(
            (
                await session.execute(
                    select(ConsultationNote)
                    .where(
                        ConsultationNote.tenant_id == hospital_id,
                        ConsultationNote.specialist_id == account.id,
                    )
                    .order_by(ConsultationNote.updated_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return {
            "identity": identity,
            "items": [
                {
                    "id": str(note.id),
                    "title": f"Ticket {note.ticket_id}",
                    "body": note.body,
                    "updated_at": note.updated_at.isoformat(),
                    "status": "SIGNED",
                }
                for note in notes
            ],
        }
    if resource == "messages":
        messages = list(
            (
                await session.execute(
                    select(SpecialistMessage)
                    .where(
                        SpecialistMessage.tenant_id == hospital_id,
                        SpecialistMessage.specialist_id == account.id,
                    )
                    .order_by(SpecialistMessage.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return {
            "identity": identity,
            "items": [
                {
                    "id": str(message.id),
                    "title": message.sender_label,
                    "body": message.body,
                    "created_at": message.created_at.isoformat(),
                    "status": "READ" if message.is_read else "UNREAD",
                }
                for message in messages
            ],
        }
    if resource == "earnings":
        completed = [row for row in appointment_rows if row[0].status == "COMPLETED"]
        fee = 15000
        return {
            "identity": identity,
            "stats": [
                {
                    "title": "Completed consultations",
                    "value": len(completed),
                    "tone": "sky",
                },
                {
                    "title": "Gross earnings",
                    "value": f"₦{len(completed) * fee:,}",
                    "tone": "violet",
                },
            ],
            "items": [
                {**item, "value": f"₦{fee:,}"}
                for item in appointment_items
                if item["status"] == "COMPLETED"
            ],
        }
    if resource == "notifications":
        return {
            "identity": identity,
            "notifications": [
                {
                    **item,
                    "title": f"Patient update · {item['ticket_number']}",
                    "type": "QUEUE_UPDATE",
                    "is_read": False,
                }
                for item in patient_items[:10]
            ],
        }
    return {
        "identity": identity,
        "items": [
            {
                "id": str(account.id),
                "title": identity["name"],
                "subtitle": account.specialty or "General Medicine",
                "status": "ACTIVE",
            }
        ],
    }


@router.patch("/specialist/patients/{ticket_id}/assign-self")
async def assign_specialist_patient(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> TicketResponse:
    account, membership = await require_specialist_workspace(request, session)
    ticket = await session.scalar(
        select(Ticket)
        .where(
            Ticket.id == uuid.UUID(ticket_id),
            ticket_destination_queue(membership.hospital_id),
        )
        .with_for_update()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    expected_department = department_for_specialty(ticket.assigned_specialty)
    if membership.department_id != expected_department or (
        ticket.assigned_specialty
        and membership.specialty_id != ticket.assigned_specialty
    ):
        raise HTTPException(
            status_code=403,
            detail="Ticket requires a matching department and specialty membership",
        )
    if ticket.assigned_specialist_id not in {None, account.id}:
        raise HTTPException(
            status_code=409, detail="Ticket is assigned to another specialist"
        )
    ticket.assigned_specialist_id = account.id
    await session.commit()
    return build_ticket_response(ticket)


@router.patch("/specialist/patients/{ticket_id}/status")
async def specialist_patient_status(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> TicketResponse:
    payload = await request.json()
    account, membership = await require_specialist_workspace(request, session)
    status = payload.get("queue_status")
    if status not in {"QUEUED", "BEING_SEEN", "RESOLVED"}:
        raise HTTPException(status_code=422, detail="Invalid queue status")
    ticket = await session.scalar(
        select(Ticket)
        .where(
            Ticket.id == uuid.UUID(ticket_id),
            ticket_destination_queue(membership.hospital_id),
        )
        .with_for_update()
    )
    if not ticket or ticket.assigned_specialist_id != account.id:
        raise HTTPException(status_code=404, detail="Assigned ticket not found")
    ticket.queue_status = status
    ticket.version += 1
    await session.commit()
    response = build_ticket_response(ticket)
    await broadcast_ticket_event(ticket, "ticket.updated", response.model_dump())
    return response


@router.patch("/specialist/patients/{ticket_id}/escalate")
async def specialist_patient_escalate(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> TicketResponse:
    return await escalate_ticket(ticket_id, request, session)


@router.post("/specialist/patients/{ticket_id}/notes", status_code=201)
async def create_consultation_note(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, membership = await require_specialist_workspace(request, session)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 3:
        raise HTTPException(status_code=422, detail="Consultation note is required")
    ticket = await session.scalar(
        select(Ticket).where(
            Ticket.id == uuid.UUID(ticket_id),
            ticket_destination_queue(membership.hospital_id),
            Ticket.assigned_specialist_id == account.id,
        )
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Assigned ticket not found")
    note = ConsultationNote(
        tenant_id=membership.hospital_id,
        ticket_id=ticket.id,
        specialist_id=account.id,
        body=body,
    )
    session.add(note)
    await session.commit()
    return {
        "id": str(note.id),
        "ticket_id": str(ticket.id),
        "body": note.body,
        "created_at": note.created_at,
    }


@router.post("/specialist/messages", status_code=201)
async def create_specialist_message(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, membership = await require_specialist_workspace(request, session)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 2:
        raise HTTPException(status_code=422, detail="Message body is required")
    message = SpecialistMessage(
        tenant_id=membership.hospital_id,
        specialist_id=account.id,
        sender_label=str(payload.get("sender_label") or "Specialist"),
        body=body,
        is_read=True,
    )
    session.add(message)
    await session.commit()
    return {
        "id": str(message.id),
        "body": message.body,
        "created_at": message.created_at,
    }
