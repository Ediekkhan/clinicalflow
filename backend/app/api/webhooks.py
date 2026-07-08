from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_tenant_id
from app.channels import sms, whatsapp
from app.db.session import get_session
from app.middleware.rate_limit_config import RATE_LIMITS
from app.middleware.rate_limiter import check_rate_limit, get_rate_limit_identifier
from app.schemas.domain import IncomingMessage, TicketCreate, TicketRead
from app.services.appointments import create_appointment, list_open_slots
from app.services.lexicon import extract_symptoms
from app.services.tickets import create_ticket, detect_duplicate_identity


router = APIRouter(prefix="/webhooks", tags=["channel-webhooks"])


@router.post("/whatsapp")
async def whatsapp_webhook(
    payload: IncomingMessage,
    request: Request,
    tenant_id=Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    config = RATE_LIMITS["webhook:whatsapp"]
    await check_rate_limit(
        key="webhook:whatsapp",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )
    if payload.intent != "REGISTER_NEW_PATIENT":
        duplicate = await detect_duplicate_identity(session, payload.phone)
        if duplicate:
            return duplicate.model_dump(mode="json")

    extracted = await extract_symptoms(payload.text)
    if extracted.dangerous_keywords:
        return {"action": "send_immediate_alert", "message": whatsapp.dangerous_keyword_alert(payload.phone)}

    ticket = await create_ticket(
        session,
        tenant_id,
        TicketCreate(
            customer_phone=payload.phone,
            account_group_phone=payload.phone,
            channel="WHATSAPP",
            raw_intake_text=payload.text,
            symptoms=extracted.symptom_ids,
            allow_duplicate_for_shared_phone=payload.intent == "REGISTER_NEW_PATIENT",
        ),
    )
    slots = await list_open_slots(session, specialty=ticket.assigned_specialty)
    return {
        "ticket": TicketRead.model_validate(ticket).model_dump(mode="json"),
        "next_message": whatsapp.slot_list_template(payload.phone, slots),
    }


@router.post("/sms")
async def sms_webhook(
    payload: IncomingMessage,
    tenant_id=Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    if payload.intent == "CANCEL":
        return {"message": "Cancellation request received. A staff member will confirm shortly."}

    duplicate = await detect_duplicate_identity(session, payload.phone)
    if duplicate and payload.intent != "REGISTER_NEW_PATIENT":
        return {
            "duplicate_detected": True,
            "message": (
                "[PROJECT_NAME]: This phone already has an active visit. "
                "Reply 1 to continue or 2 to register another patient."
            ),
        }

    if payload.intent == "BOOK_SLOT" and payload.selected_slot_id:
        # The most recent active ticket on this phone receives the slot.
        from app.services.tickets import active_tickets_for_phone

        active = await active_tickets_for_phone(session, payload.phone)
        if not active:
            return {"message": "[PROJECT_NAME]: No active ticket found for this phone."}
        _appointment, outbound = await create_appointment(
            session, tenant_id, active[0].id, payload.selected_slot_id, "SMS"
        )
        return {"message": outbound}

    extracted = await extract_symptoms(payload.text)
    ticket = await create_ticket(
        session,
        tenant_id,
        TicketCreate(
            customer_phone=payload.phone,
            account_group_phone=payload.phone,
            channel="SMS",
            raw_intake_text=payload.text,
            symptoms=extracted.symptom_ids,
        ),
    )
    return {"message": sms.queue_assignment(ticket.ticket_number, ticket.urgency_level)}
