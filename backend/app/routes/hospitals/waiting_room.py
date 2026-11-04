from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/waiting-room")
async def hospital_waiting_room(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, membership, _tenant = await require_hospital_membership(
        request, session, roles={"doctor", "nurse", "hospital_admin"}
    )
    result = await session.execute(
        select(Ticket)
        .where(
            ticket_destination_queue(membership.hospital_id),
            Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]),
        )
        .order_by(Ticket.created_at.asc())
    )
    tickets = list(result.scalars().all())
    now_serving_ticket = next(
        (ticket for ticket in reversed(tickets) if ticket.queue_status == "BEING_SEEN"),
        None,
    )
    urgency_order = {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}
    queued = sorted(
        (ticket for ticket in tickets if ticket.queue_status == "QUEUED"),
        key=lambda ticket: (
            urgency_order.get(ticket.urgency_level, 3),
            ticket.created_at,
        ),
    )
    now_serving = None
    if now_serving_ticket:
        now_serving = {
            "ticket_number": now_serving_ticket.ticket_number,
            "room_label": now_serving_ticket.assigned_specialty or "Triage Room",
        }
    departments: dict[str, dict[str, Any]] = {}
    for ticket in tickets:
        name = ticket.assigned_specialty or "Front Desk"
        row = departments.setdefault(
            name, {"name": name, "waiting": 0, "being_seen": 0, "resolved": 0}
        )
        row["being_seen" if ticket.queue_status == "BEING_SEEN" else "waiting"] += 1
    return {
        "now_serving": now_serving,
        "up_next": [
            {
                "id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "room_label": ticket.assigned_specialty or "Front Desk",
            }
            for ticket in queued[:4]
        ],
        "departments": list(departments.values()),
    }
