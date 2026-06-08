from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import Specialist, Ticket
from app.schemas.synaptiverse import SpecialistRead, SynTicketRead


router = APIRouter(prefix="/specialists", tags=["specialists"])


@router.get("/{specialist_id}", response_model=SpecialistRead)
async def specialist_profile(
    specialist_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    specialist = await session.get(Specialist, specialist_id)
    if specialist is None:
        raise LookupError("Specialist not found.")
    return SpecialistRead.model_validate(specialist)


@router.get("/{specialist_id}/tickets", response_model=list[SynTicketRead])
async def specialist_tickets(
    specialist_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    tickets = (
        await session.scalars(
            select(Ticket)
            .where(Ticket.assigned_specialist_id == specialist_id)
            .order_by(Ticket.created_at.desc())
        )
    ).all()
    return [SynTicketRead.model_validate(ticket) for ticket in tickets]

