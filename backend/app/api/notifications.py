from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import Notification
from app.schemas.synaptiverse import NotificationRead


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    recipient_id: UUID,
    unread_only: bool = False,
    session: AsyncSession = Depends(get_session),
):
    statement = select(Notification).where(Notification.recipient_id == recipient_id).order_by(Notification.created_at.desc())
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    return [NotificationRead.model_validate(item) for item in (await session.scalars(statement)).all()]


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    notification = await session.get(Notification, notification_id)
    if notification is None:
        raise LookupError("Notification not found.")
    notification.is_read = True
    await session.flush()
    return NotificationRead.model_validate(notification)

