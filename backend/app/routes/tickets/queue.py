from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[TicketResponse]:
    account = await require_account(request, session)
    query = select(Ticket)
    if account.role == "patient":
        if not account.phone:
            return []
        query = query.where(Ticket.customer_phone == account.phone)
    elif account.role in {"specialist", "doctor", "nurse", "hospital_admin", "admin"}:
        query = query.where(ticket_visible_to_tenant(account.tenant_id))
    else:
        raise HTTPException(status_code=403, detail="Queue access not permitted")
    result = await session.execute(query.order_by(Ticket.created_at.desc()))
    tickets = result.scalars().all()
    if account.role == "patient":
        await write_audit_log(
            session,
            AuditAction.PATIENT_RECORD_VIEWED,
            actor_id=str(account.id),
            actor_type="PATIENT",
            tenant_id=str(account.tenant_id),
            ip_address=request.client.host if request.client else "127.0.0.1",
            resource_type="TicketCollection",
            metadata={"record_count": len(tickets)},
        )
        await session.commit()
    return [build_ticket_response(ticket) for ticket in tickets]


@router.patch("/tickets/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> TicketResponse:
    account = await require_roles(
        request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"}
    )
    tenant_id = str(account.tenant_id)
    resource_id = uuid.UUID(ticket_id)
    idempotency_key = request.headers.get("x-idempotency-key")
    replay = await replayed_mutation(
        session, account.tenant_id, idempotency_key, "TICKET_ESCALATE", resource_id
    )
    if replay:
        return replay
    ticket = await session.scalar(
        select(Ticket)
        .where(Ticket.id == resource_id, ticket_visible_to_tenant(account.tenant_id))
        .with_for_update()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replay = await replayed_mutation(
        session, account.tenant_id, idempotency_key, "TICKET_ESCALATE", resource_id
    )
    if replay:
        return replay
    expected_header = request.headers.get("x-expected-version")
    try:
        expected_version = int(expected_header) if expected_header else None
    except ValueError as error:
        raise HTTPException(
            status_code=400, detail="Expected version must be an integer"
        ) from error
    if expected_version is not None and ticket.version != expected_version:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Ticket changed on another device",
                "current": build_ticket_response(ticket).model_dump(mode="json"),
            },
        )
    ticket.urgency_level = "CRITICAL"
    ticket.is_manually_escalated = True
    ticket.queue_status = "QUEUED"
    ticket.version += 1
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.TICKET_ESCALATED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=tenant_id,
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Ticket",
        resource_id=ticket_id,
        metadata={"manual_escalation": True},
    )
    response = build_ticket_response(ticket)
    if idempotency_key:
        session.add(
            ClientMutation(
                tenant_id=account.tenant_id,
                idempotency_key=idempotency_key,
                action="TICKET_ESCALATE",
                resource_id=resource_id,
                response_json=response.model_dump_json(),
            )
        )
    await session.commit()
    await broadcast_ticket_event(
        ticket, "ticket.escalated", response.model_dump(), "HIGH"
    )
    return response


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TicketResponse:
    account = await require_roles(
        request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"}
    )
    tenant_id = str(account.tenant_id)
    resource_id = uuid.UUID(ticket_id)
    idempotency_key = request.headers.get("x-idempotency-key")
    replay = await replayed_mutation(
        session, account.tenant_id, idempotency_key, "TICKET_UPDATE", resource_id
    )
    if replay:
        return replay
    ticket = await session.scalar(
        select(Ticket)
        .where(Ticket.id == resource_id, ticket_visible_to_tenant(account.tenant_id))
        .with_for_update()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replay = await replayed_mutation(
        session, account.tenant_id, idempotency_key, "TICKET_UPDATE", resource_id
    )
    if replay:
        return replay
    if (
        payload.expected_version is not None
        and ticket.version != payload.expected_version
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Ticket changed on another device",
                "current": build_ticket_response(ticket).model_dump(mode="json"),
            },
        )
    if payload.queue_status is not None:
        ticket.queue_status = payload.queue_status
    if payload.urgency_level is not None:
        ticket.urgency_level = payload.urgency_level
    if payload.is_manually_escalated is not None:
        ticket.is_manually_escalated = payload.is_manually_escalated
    ticket.version += 1
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.TICKET_STATUS_CHANGED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=tenant_id,
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Ticket",
        resource_id=ticket_id,
    )
    response = build_ticket_response(ticket)
    if idempotency_key:
        session.add(
            ClientMutation(
                tenant_id=account.tenant_id,
                idempotency_key=idempotency_key,
                action="TICKET_UPDATE",
                resource_id=resource_id,
                response_json=response.model_dump_json(),
            )
        )
    await session.commit()
    await broadcast_ticket_event(ticket, "ticket.updated", response.model_dump())
    return response
