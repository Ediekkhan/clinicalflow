from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.whatsapp import duplicate_identity_menu
from app.models.domain import AuditLog, Ticket
from app.schemas.domain import DuplicateIntentResponse, TicketCreate, TicketRead, WebSocketEvent
from app.services.lexicon import extract_symptoms
from app.services.realtime import connection_manager
from app.services.triage_graph import derive_triage


ACTIVE_QUEUE_STATUSES = ("QUEUED", "BEING_SEEN")


async def generate_ticket_number(session: AsyncSession) -> str:
    year = datetime.now(UTC).year
    count = await session.scalar(select(func.count()).select_from(Ticket))
    return f"SV-{year}-{int(count or 0) + 1:04d}"


def active_tickets_for_phone_query(phone: str) -> Select[tuple[Ticket]]:
    return (
        select(Ticket)
        .where(Ticket.customer_phone == phone)
        .where(Ticket.queue_status.in_(ACTIVE_QUEUE_STATUSES))
        .order_by(Ticket.created_at.desc())
    )


async def active_tickets_for_phone(session: AsyncSession, phone: str) -> list[Ticket]:
    return list((await session.scalars(active_tickets_for_phone_query(phone))).all())


async def detect_duplicate_identity(
    session: AsyncSession,
    phone: str,
) -> DuplicateIntentResponse | None:
    active = await active_tickets_for_phone(session, phone)
    if not active:
        return None
    return DuplicateIntentResponse(
        account_group_phone=active[0].account_group_phone,
        active_ticket_numbers=[ticket.ticket_number for ticket in active],
        interactive_menu=duplicate_identity_menu(phone, [ticket.ticket_number for ticket in active]),
    )


async def create_ticket(
    session: AsyncSession,
    tenant_id: UUID,
    payload: TicketCreate,
) -> Ticket:
    account_group_phone = payload.account_group_phone or payload.customer_phone
    extracted = await extract_symptoms(payload.raw_intake_text or "")
    symptoms = payload.symptoms or extracted.symptom_ids
    decision = await derive_triage(symptoms)
    urgency = "CRITICAL" if extracted.dangerous_keywords else decision.derived_urgency

    ticket = Ticket(
        tenant_id=tenant_id,
        ticket_number=await generate_ticket_number(session),
        customer_phone=payload.customer_phone,
        account_group_phone=account_group_phone,
        channel=payload.channel,
        urgency_level=urgency,
        matched_condition_id=decision.condition_id,
        assigned_specialty=decision.target_specialty,
        queue_status="QUEUED",
        appointment_slot=payload.appointment_slot,
        raw_intake_text=payload.raw_intake_text,
        extracted_symptoms=",".join(symptoms),
    )
    session.add(ticket)
    await session.flush()
    await connection_manager.broadcast(
        WebSocketEvent(
            type="ticket.created",
            tenant_id=tenant_id,
            payload=TicketRead.model_validate(ticket).model_dump(mode="json"),
            priority="HIGH" if urgency == "CRITICAL" else "NORMAL",
        )
    )
    return ticket


async def escalate_ticket(
    session: AsyncSession,
    tenant_id: UUID,
    ticket_id: UUID,
    staff_id: UUID | None,
    ip_address: str | None,
) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise LookupError("Ticket not found.")

    ticket.is_manually_escalated = True
    ticket.urgency_level = "CRITICAL"
    ticket.queue_status = "QUEUED"
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            staff_id=staff_id,
            action=f"FORCED_OVERTAKE ticket={ticket.ticket_number}",
            ip_address=ip_address,
        )
    )
    await session.flush()
    await connection_manager.broadcast(
        WebSocketEvent(
            type="ticket.escalated",
            tenant_id=tenant_id,
            payload=TicketRead.model_validate(ticket).model_dump(mode="json"),
            priority="HIGH",
        )
    )
    return ticket

