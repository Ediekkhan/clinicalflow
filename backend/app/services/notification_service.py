from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Notification
from app.schemas.synaptiverse import NotificationRead
from app.services.realtime import connection_manager


async def create_notification(
    session: AsyncSession,
    tenant_id: UUID,
    recipient_type: str,
    recipient_id: UUID,
    title: str,
    body: str,
    ticket_id: UUID | None = None,
) -> Notification:
    notification = Notification(
        tenant_id=tenant_id,
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        title=title,
        body=body,
        ticket_id=ticket_id,
    )
    session.add(notification)
    await session.flush()
    payload = {"type": "notification.created", "payload": NotificationRead.model_validate(notification).model_dump(mode="json")}
    if recipient_type == "SPECIALIST":
        await connection_manager.broadcast_specialist(recipient_id, payload)
    return notification

