from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403
from app.routes.appointments.routes import book_appointment

router = APIRouter(prefix="/api/v1")


@router.post("/tickets", response_model=TicketResponse, status_code=201)
async def create_ticket(
    payload: TicketCreate, request: Request, session: AsyncSession = Depends(get_db)
) -> TicketResponse:
    await enforce_rate_limit(
        request,
        "public-intake",
        settings.public_intake_rate_limit,
        payload.customer_phone,
    )
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    if not await tenant_control(session, tenant_id, "intake_enabled", True):
        raise HTTPException(
            status_code=503, detail="Clinic intake is temporarily paused"
        )
    clinical_route = await request.app.state.knowledge_graph.route(
        payload.raw_intake_text
    )
    return await persist_ticket(payload, request, session, clinical_route)


@router.post("/channels/{channel}/intake", response_model=ChannelIntakeResponse)
async def channel_intake(
    channel: str,
    payload: ChannelIntakeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ChannelIntakeResponse:
    normalized_channel = channel.upper()
    if normalized_channel not in {"WHATSAPP", "SMS"}:
        raise HTTPException(status_code=404, detail="Channel not supported")

    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    result = await session.execute(
        select(Ticket)
        .where(
            Ticket.tenant_id == tenant_id,
            Ticket.customer_phone == payload.customer_phone,
            Ticket.queue_status.notin_(
                ["REJECTED", "DISCHARGED", "TRANSFERRED", "CANCELLED", "RESOLVED"]
            ),
        )
        .order_by(Ticket.created_at.desc())
    )
    active_ticket = result.scalars().first()
    channel_name = "WHATSAPP" if normalized_channel == "WHATSAPP" else "SMS"

    if active_ticket and payload.intent is None:
        menu = [
            ChannelMenuOption(
                id="CONTINUE_EXISTING",
                title="Continue existing visit",
                description=f"Use ticket {active_ticket.ticket_number}.",
            ),
            ChannelMenuOption(
                id="REGISTER_NEW_PATIENT",
                title="Register a new patient",
                description="Create a separate ticket linked to this shared phone.",
            ),
            ChannelMenuOption(
                id="BOOK_APPOINTMENT",
                title="Book an appointment",
                description="Show the next available provider times.",
            ),
        ]
        message = (
            "An active visit already uses this phone. Choose who this message is for."
            if channel_name == "WHATSAPP"
            else "Active visit found. Reply 1 CONTINUE, 2 NEW PATIENT, or 3 BOOK."
        )
        return ChannelIntakeResponse(
            action="SHOW_IDENTITY_MENU",
            channel=channel_name,
            message=message,
            active_ticket_id=active_ticket.id,
            account_group_phone=payload.customer_phone,
            menu=menu,
        )

    if payload.intent == "CONTINUE_EXISTING":
        if not active_ticket:
            raise HTTPException(
                status_code=404, detail="No active visit for this phone"
            )
        return ChannelIntakeResponse(
            action="CONTINUE_EXISTING",
            channel=channel_name,
            message=f"Continuing ticket {active_ticket.ticket_number}.",
            active_ticket_id=active_ticket.id,
            account_group_phone=active_ticket.account_group_phone
            or payload.customer_phone,
        )

    if payload.intent == "BOOK_APPOINTMENT":
        if not active_ticket:
            raise HTTPException(
                status_code=404, detail="No active visit for this phone"
            )
        slot_rows = (
            await session.execute(
                select(ProviderSlot, Provider)
                .join(Provider, Provider.id == ProviderSlot.provider_id)
                .where(
                    ProviderSlot.tenant_id == tenant_id,
                    ProviderSlot.is_locked.is_(False),
                    ProviderSlot.is_booked.is_(False),
                    Provider.is_active.is_(True),
                    Provider.specialty == active_ticket.assigned_specialty,
                )
                .order_by(ProviderSlot.starts_at.asc())
                .limit(5)
            )
        ).all()
        slot_menu = [
            ChannelMenuOption(
                id=str(slot.id),
                title=slot.starts_at.strftime("%a %d %b, %H:%M"),
                description=f"{provider.full_name} · {provider.specialty} · {provider.room_label}",
            )
            for slot, provider in slot_rows
        ]
        return ChannelIntakeResponse(
            action="SHOW_SLOT_MENU",
            channel=channel_name,
            message=(
                "Select an available appointment time."
                if slot_menu
                else "No appointment slots are currently available."
            ),
            active_ticket_id=active_ticket.id,
            account_group_phone=payload.customer_phone,
            menu=slot_menu,
        )

    if payload.intent == "CONFIRM_APPOINTMENT":
        if not active_ticket or not payload.slot_id:
            raise HTTPException(
                status_code=422,
                detail="An active ticket and selected slot are required",
            )
        booked = await book_appointment(
            AppointmentCreate(
                ticket_id=active_ticket.id,
                slot_id=payload.slot_id,
                customer_phone=payload.customer_phone,
            ),
            request,
            session,
        )
        return ChannelIntakeResponse(
            action="APPOINTMENT_BOOKED",
            channel=channel_name,
            message=f"Appointment confirmed for {booked.starts_at.strftime('%a %d %b at %H:%M')} with {booked.provider_name}.",
            active_ticket_id=active_ticket.id,
            account_group_phone=active_ticket.account_group_phone
            or payload.customer_phone,
        )

    if payload.intent == "CANCEL_APPOINTMENT":
        appointment = await session.scalar(
            select(Appointment)
            .where(
                Appointment.tenant_id == tenant_id,
                Appointment.customer_phone == payload.customer_phone,
                Appointment.status == "BOOKED",
            )
            .order_by(Appointment.created_at.desc())
            .with_for_update()
        )
        if not appointment:
            raise HTTPException(
                status_code=404, detail="No active appointment for this phone"
            )
        slot = await session.scalar(
            select(ProviderSlot)
            .where(ProviderSlot.id == appointment.slot_id)
            .with_for_update()
        )
        appointment.status = "CANCELLED"
        appointment.updated_at = utc_now()
        if slot:
            slot.is_booked = False
        ticket = await session.get(Ticket, appointment.ticket_id)
        if ticket:
            ticket.appointment_slot = None
        await session.commit()
        return ChannelIntakeResponse(
            action="APPOINTMENT_CANCELLED",
            channel=channel_name,
            message="Appointment cancelled. Reply BOOK to choose another time.",
            active_ticket_id=appointment.ticket_id,
            account_group_phone=payload.customer_phone,
        )

    if not payload.raw_intake_text or len(payload.raw_intake_text.strip()) < 3:
        raise HTTPException(
            status_code=422, detail="Describe the patient's main concern"
        )

    ticket_payload = TicketCreate(
        customer_phone=payload.customer_phone,
        raw_intake_text=payload.raw_intake_text,
        channel=channel_name,
        account_group_phone=(
            payload.customer_phone if payload.intent == "REGISTER_NEW_PATIENT" else None
        ),
    )
    created = await create_ticket(ticket_payload, request, session)
    return ChannelIntakeResponse(
        action="TICKET_CREATED",
        channel=channel_name,
        message=f"Ticket {created.ticket_number} has been created.",
        active_ticket_id=created.id,
        account_group_phone=created.account_group_phone,
        ticket=created,
    )


@router.get("/channels/templates")
async def channel_templates() -> dict[str, Any]:
    return {
        "sms": [
            {"id": key, "body": value, "max_segments": 2}
            for key, value in SMS_TEMPLATES.items()
        ]
    }


@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")
    if mode != "subscribe" or token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return Response(content=challenge, media_type="text/plain")


@router.post("/webhooks/{channel}")
async def channel_webhook(
    channel: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    normalized_channel = channel.lower()
    if normalized_channel not in {"whatsapp", "sms"}:
        raise HTTPException(status_code=404, detail="Channel not supported")
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256") or request.headers.get(
        "x-clinicalflow-signature"
    )
    if not valid_signature(body, signature, settings.channel_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        provider_event = normalize_webhook(normalized_channel, json.loads(body))
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=422, detail="Unsupported webhook payload"
        ) from error
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    message_id = str(provider_event.get("message_id") or uuid.uuid4())
    if provider_event.get("status"):
        record = await session.scalar(
            select(OperationalRecord)
            .where(
                OperationalRecord.tenant_id == tenant_id,
                OperationalRecord.entity == normalized_channel,
                OperationalRecord.resource == "messages",
                OperationalRecord.title == message_id,
            )
            .order_by(OperationalRecord.created_at.desc())
        )
        if record:
            record.status = str(provider_event["status"]).upper()
            record.updated_at = utc_now()
        else:
            session.add(
                OperationalRecord(
                    tenant_id=tenant_id,
                    entity=normalized_channel,
                    resource="messages",
                    title=message_id,
                    description="Provider delivery receipt",
                    status=str(provider_event["status"]).upper(),
                )
            )
        await session.commit()
        return {
            "accepted": True,
            "message_id": message_id,
            "delivery_status": str(provider_event["status"]).upper(),
        }
    text_value = str(provider_event.get("text") or "").strip()
    intent = provider_event.get("intent") or intent_from_text(text_value)
    payload = ChannelIntakeRequest(
        customer_phone=str(provider_event.get("from") or ""),
        raw_intake_text=text_value if not intent else None,
        intent=intent,
        slot_id=provider_event.get("slot_id"),
    )
    result = await channel_intake(normalized_channel, payload, request, session)
    session.add(
        OperationalRecord(
            tenant_id=tenant_id,
            entity=normalized_channel,
            resource="messages",
            title=message_id,
            description=result.message,
            status="QUEUED",
        )
    )
    await session.commit()
    return {
        "accepted": True,
        "message_id": message_id,
        "reply": result.model_dump(mode="json"),
    }
