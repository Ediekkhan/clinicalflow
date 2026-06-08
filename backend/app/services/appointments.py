from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels import whatsapp
from app.channels.sms import booking_confirmation as sms_booking_confirmation
from app.models.domain import Appointment, ProviderSlot, Ticket
from app.schemas.domain import WebSocketEvent
from app.services.realtime import connection_manager


async def list_open_slots(
    session: AsyncSession,
    starts_after: datetime | None = None,
    specialty: str | None = None,
) -> list[ProviderSlot]:
    filters = [ProviderSlot.is_locked.is_(False)]
    if starts_after:
        filters.append(ProviderSlot.starts_at >= starts_after)
    if specialty:
        filters.append(ProviderSlot.specialty == specialty)
    occupied = select(Appointment.provider_slot_id).where(Appointment.status == "BOOKED")
    statement = (
        select(ProviderSlot)
        .where(and_(*filters))
        .where(ProviderSlot.id.not_in(occupied))
        .order_by(ProviderSlot.starts_at.asc())
        .limit(50)
    )
    return list((await session.scalars(statement)).all())


async def create_appointment(
    session: AsyncSession,
    tenant_id: UUID,
    ticket_id: UUID,
    provider_slot_id: UUID,
    channel_origin: str,
) -> tuple[Appointment, dict[str, object] | str]:
    ticket = await session.get(Ticket, ticket_id)
    slot = await session.get(ProviderSlot, provider_slot_id)
    if ticket is None or slot is None:
        raise LookupError("Ticket or provider slot not found.")
    if slot.is_locked:
        raise ValueError("Provider slot is locked.")

    appointment = Appointment(
        tenant_id=tenant_id,
        ticket_id=ticket_id,
        provider_slot_id=provider_slot_id,
        channel_origin=channel_origin,
    )
    ticket.appointment_slot = slot.starts_at
    session.add(appointment)
    await session.flush()

    await connection_manager.broadcast(
        WebSocketEvent(
            type="appointment.updated",
            tenant_id=tenant_id,
            payload={
                "appointment_id": str(appointment.id),
                "ticket_id": str(ticket_id),
                "provider_slot_id": str(provider_slot_id),
                "starts_at": slot.starts_at.isoformat(),
                "room_label": slot.room_label,
            },
        )
    )

    if channel_origin == "SMS":
        return appointment, sms_booking_confirmation(ticket.ticket_number, slot.starts_at)
    return appointment, whatsapp.booking_confirmation(ticket, slot.starts_at)


async def lock_slot(
    session: AsyncSession,
    tenant_id: UUID,
    slot_id: UUID,
    is_locked: bool,
    reason: str | None,
) -> ProviderSlot:
    slot = await session.get(ProviderSlot, slot_id)
    if slot is None:
        raise LookupError("Provider slot not found.")
    slot.is_locked = is_locked
    slot.lock_reason = reason if is_locked else None
    await session.flush()
    await connection_manager.broadcast(
        WebSocketEvent(
            type="appointment.updated",
            tenant_id=tenant_id,
            payload={
                "slot_id": str(slot.id),
                "is_locked": slot.is_locked,
                "lock_reason": slot.lock_reason,
            },
            priority="HIGH" if is_locked else "NORMAL",
        )
    )
    return slot

