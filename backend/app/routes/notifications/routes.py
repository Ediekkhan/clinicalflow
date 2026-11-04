from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.websocket("/ws/triage")
@router.websocket("/ws/notifications")
async def triage_websocket(websocket: WebSocket) -> None:
    token = websocket.cookies.get(ACCESS_COOKIE)
    async with websocket.app.state.session_factory() as session:
        authenticated = (
            await account_for_access_token(session, token) if token else None
        )
    if not authenticated:
        await websocket.close(code=4401, reason="Authentication required")
        return
    tenant_key = str(authenticated[0].tenant_id)
    await triage_manager.connect(tenant_key, str(authenticated[0].id), websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        triage_manager.disconnect(tenant_key, websocket)


@router.get("/notifications")
async def notifications(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    memberships = (
        await active_staff_memberships(session, account)
        if account.role != "patient"
        else []
    )
    membership_ids = [membership.id for membership in memberships]
    notification_filters = [
        Notification.recipient_user_id == account.id,
        Notification.recipient_account_id == account.id,
    ]
    if membership_ids:
        notification_filters.append(
            Notification.recipient_membership_id.in_(membership_ids)
        )
    stored_notifications = list(
        (
            await session.execute(
                select(Notification)
                .where(
                    Notification.tenant_id.in_(
                        [membership.hospital_id for membership in memberships]
                        or [account.tenant_id]
                    ),
                    or_(*notification_filters),
                )
                .order_by(Notification.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    rows = [
        {
            "id": str(notification.id),
            "recipient_type": notification.recipient_role.upper(),
            "recipient_id": (
                str(notification.recipient_user_id or notification.recipient_account_id)
                if (notification.recipient_user_id or notification.recipient_account_id)
                else None
            ),
            "recipient_membership_id": (
                str(notification.recipient_membership_id)
                if notification.recipient_membership_id
                else None
            ),
            "hospital_id": (
                str(notification.hospital_id) if notification.hospital_id else None
            ),
            "department_id": notification.department_id,
            "title": notification.title,
            "body": notification.body or "",
            "priority": notification.priority,
            "is_read": notification.is_read,
            "read_at": notification.read_at,
            "acknowledged_at": notification.acknowledged_at,
            "requires_acknowledgement": notification.event_type
            in {
                "APPOINTMENT_ASSIGNED",
                "APPOINTMENT_REMINDER",
                "PATIENT_CHECKED_IN",
            },
            "ticket_id": (
                str(notification.ticket_id) if notification.ticket_id else None
            ),
            "appointment_id": (
                str(notification.appointment_id)
                if notification.appointment_id
                else None
            ),
            "type": (
                notification.event_type.lower().replace("_", ".")
                if notification.event_type.startswith("APPOINTMENT_")
                else notification.event_type
            ),
            "event_type": notification.event_type,
            "created_at": notification.created_at,
        }
        for notification in stored_notifications
    ]
    ticket_query = select(Ticket)
    if account.role == "patient":
        ticket_query = ticket_query.where(Ticket.customer_phone == account.phone)
    elif memberships:
        visible_pairs = {
            (membership.hospital_id, membership.department_id)
            for membership in memberships
        }
        ticket_query = ticket_query.where(
            or_(
                *[
                    ticket_visible_to_tenant(hospital_id)
                    for hospital_id, _department_id in visible_pairs
                ]
            ),
            or_(
                *[
                    Ticket.assigned_specialty == department_id
                    for _hospital_id, department_id in visible_pairs
                ]
            ),
        )
    else:
        ticket_query = ticket_query.where(False)
    tickets = list(
        (
            await session.execute(
                ticket_query.order_by(Ticket.created_at.desc()).limit(20)
            )
        )
        .scalars()
        .all()
    )
    marker_prefix = f"{account.id}:"
    markers = list(
        (
            await session.execute(
                select(OperationalRecord).where(
                    OperationalRecord.tenant_id == account.tenant_id,
                    OperationalRecord.entity == "notification",
                    OperationalRecord.resource == "read",
                    OperationalRecord.title.like(f"{marker_prefix}%"),
                )
            )
        )
        .scalars()
        .all()
    )
    read_ids = {marker.title.removeprefix(marker_prefix) for marker in markers}
    rows.extend(
        {
            "id": str(ticket.id),
            "recipient_type": (
                "PATIENT" if account.role == "patient" else account.role.upper()
            ),
            "recipient_id": str(account.id),
            "title": f"Queue update · {ticket.ticket_number}",
            "body": f"{ticket.queue_status.replace('_', ' ').title()} · {ticket.assigned_specialty or 'Front Desk'}",
            "is_read": str(ticket.id) in read_ids,
            "ticket_id": str(ticket.id),
            "urgency_level": ticket.urgency_level,
            "condition_name": ticket.matched_condition_id,
            "type": "QUEUE_UPDATE",
            "created_at": ticket.created_at,
        }
        for ticket in tickets
    )
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)


@router.patch("/notifications/read-all")
async def mark_all_notifications_read(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, bool]:
    account = await require_account(request, session)
    for row in await notifications(request, session):
        await mark_notification(session, account, row["id"])
    await session.commit()
    return {"ok": True}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, bool]:
    account = await require_account(request, session)
    await mark_notification(session, account, notification_id)
    await session.commit()
    return {"ok": True}


@router.patch("/notifications/{notification_id}/acknowledge")
async def acknowledge_notification(
    notification_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    try:
        parsed_id = uuid.UUID(notification_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Notification not found") from error
    memberships = (
        await active_staff_memberships(session, account)
        if account.role != "patient"
        else []
    )
    filters = [
        Notification.recipient_user_id == account.id,
        Notification.recipient_account_id == account.id,
    ]
    if memberships:
        filters.append(
            Notification.recipient_membership_id.in_(
                [membership.id for membership in memberships]
            )
        )
    notification = await session.scalar(
        select(Notification)
        .where(Notification.id == parsed_id, or_(*filters))
        .with_for_update()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    acknowledged_at = utc_now()
    notification.is_read = True
    notification.read_at = notification.read_at or acknowledged_at
    notification.acknowledged_at = acknowledged_at
    notification.acknowledged_by_account_id = account.id
    await session.commit()
    return {"ok": True, "acknowledged_at": acknowledged_at}
