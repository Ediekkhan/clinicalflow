from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_tenant_id
from app.db.session import get_session
from app.models.domain import Ticket
from app.schemas.domain import DuplicateIntentResponse, TicketCreate, TicketRead, TicketUpdate, WebSocketEvent
from app.services.realtime import connection_manager
from app.services.tickets import create_ticket, detect_duplicate_identity, escalate_ticket


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketRead])
async def list_tickets(
    queue_status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[TicketRead]:
    statement = select(Ticket).order_by(Ticket.created_at.asc())
    if queue_status:
        statement = statement.where(Ticket.queue_status == queue_status)
    tickets = (await session.scalars(statement)).all()
    return [TicketRead.model_validate(ticket) for ticket in tickets]


@router.post("", response_model=TicketRead | DuplicateIntentResponse)
async def intake_ticket(
    payload: TicketCreate,
    tenant_id: UUID = Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    if not payload.allow_duplicate_for_shared_phone:
        duplicate = await detect_duplicate_identity(session, payload.customer_phone)
        if duplicate:
            return duplicate
    ticket = await create_ticket(session, tenant_id, payload)
    return TicketRead.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    tenant_id: UUID = Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> TicketRead:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    await session.flush()
    await connection_manager.broadcast(
        WebSocketEvent(
            type="ticket.updated",
            tenant_id=tenant_id,
            payload=TicketRead.model_validate(ticket).model_dump(mode="json"),
        )
    )
    return TicketRead.model_validate(ticket)


@router.patch("/{ticket_id}/escalate", response_model=TicketRead)
async def force_overtake(
    ticket_id: UUID,
    request: Request,
    tenant_id: UUID = Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> TicketRead:
    try:
        ticket = await escalate_ticket(
            session=session,
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            staff_id=request.state.staff_id,
            ip_address=request.client.host if request.client else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TicketRead.model_validate(ticket)

