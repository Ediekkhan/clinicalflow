from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Appointment, AuthAccount, AuthSession, AuditLog, ClientMutation, ConsultationNote, DemoRequest, HospitalDoctorMembership, Notification, OperationalRecord, Provider, ProviderSlot, SpecialistMessage, Ticket, Tenant
from app.schemas import AppointmentCreate, AppointmentMoveRequest, AppointmentResponse, AuthLoginRequest, AuthProfileResponse, AuthRefreshResponse, AuthSessionResponse, ChannelIntakeRequest, ChannelIntakeResponse, ChannelMenuOption, DemoRequestCreate, DemoRequestResponse, HospitalLoginRequest, PatientCardUpdate, PatientProfileUpdate, PinLoginRequest, SlotLockRequest, TicketCreate, TicketResponse, TicketUpdate, SlotResponse
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, account_for_access_token, apply_tenant_context, create_session, find_account, session_for_refresh_token, utc_now, verify_password
from app.services.channel_service import SMS_TEMPLATES, intent_from_text, normalize_webhook, valid_signature
from app.services.facility_routing import select_nearest_eligible_hospital, valid_coordinates

router = APIRouter(prefix="/api/v1")

KNOWN_SYMPTOM_TERMS = (
    "bleeding", "breathing", "chest pain", "cough", "dizziness", "fever",
    "headache", "nausea", "pain", "rash", "vomiting", "weakness",
)

def extract_symptom_terms(intake_text: str) -> str | None:
    normalized = intake_text.casefold()
    matches = [term for term in KNOWN_SYMPTOM_TERMS if term in normalized]
    return json.dumps(matches) if matches else None

def severity_for_urgency(urgency: str) -> str:
    return {"CRITICAL": "SEVERE", "URGENT": "MODERATE", "ROUTINE": "MILD"}.get(urgency, "MILD")

def severity_message_for_urgency(urgency: str) -> str:
    if urgency == "CRITICAL":
        return "Severe presentation. Seek emergency care immediately."
    if urgency == "URGENT":
        return "Moderate presentation. A clinician should review this today."
    return "Mild presentation. Book routine care unless symptoms worsen."


def possible_illness_for_route(condition_id: str, symptom_ids: list[str]) -> str:
    symptom_set = set(symptom_ids)
    if condition_id == "emergency_red_flag":
        if "chest_pain" in symptom_set or "difficulty_breathing" in symptom_set:
            return "Possible serious heart or breathing-related emergency"
        if "severe_bleeding" in symptom_set:
            return "Possible severe bleeding or injury-related emergency"
        return "Possible medical emergency"
    if condition_id == "acute_systemic_illness":
        if "fever" in symptom_set and "cough" in symptom_set:
            return "Possible respiratory infection or flu-like illness"
        if "fever" in symptom_set and ("vomiting" in symptom_set or "weakness" in symptom_set):
            return "Possible malaria-like or systemic infection"
        return "Possible acute infection or systemic illness"
    if condition_id == "dermatological_complaint":
        return "Possible skin irritation, allergy, or rash-related illness"
    return "No specific illness pattern identified yet"


def coordinate_value(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Patient latitude and longitude must be valid numbers")


def patient_coordinates_from_payload(payload: dict[str, Any]) -> tuple[float, float]:
    latitude = coordinate_value(payload, "latitude")
    longitude = coordinate_value(payload, "longitude")
    if latitude is None or longitude is None:
        raise HTTPException(status_code=422, detail="Patient location is required to route this ticket to the nearest registered hospital")
    if not valid_coordinates(latitude, longitude):
        raise HTTPException(status_code=422, detail="Patient coordinates are outside the valid latitude/longitude range")
    return latitude, longitude


def ticket_visible_to_tenant(tenant_id: uuid.UUID):
    return or_(Ticket.tenant_id == tenant_id, Ticket.routed_tenant_id == tenant_id)


def ticket_destination_queue(tenant_id: uuid.UUID):
    return or_(Ticket.routed_tenant_id == tenant_id, (Ticket.routed_tenant_id.is_(None) & (Ticket.tenant_id == tenant_id)))


def ticket_destination_id(ticket: Ticket) -> uuid.UUID:
    return ticket.routed_tenant_id or ticket.tenant_id


def build_ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id, tenant_id=ticket.tenant_id, ticket_number=ticket.ticket_number,
        customer_phone=ticket.customer_phone, account_group_phone=ticket.account_group_phone,
        channel=ticket.channel, urgency_level=ticket.urgency_level,
        matched_condition_id=ticket.matched_condition_id, assigned_specialty=ticket.assigned_specialty,
        queue_status=ticket.queue_status, is_manually_escalated=ticket.is_manually_escalated,
        appointment_slot=ticket.appointment_slot, patient_latitude=ticket.patient_latitude,
        patient_longitude=ticket.patient_longitude, routed_tenant_id=ticket.routed_tenant_id,
        route_distance_km=ticket.route_distance_km, created_at=ticket.created_at,
        raw_intake_text=ticket.raw_intake_text, extracted_symptoms=ticket.extracted_symptoms,
        version=ticket.version,
    )

async def replayed_mutation(session: AsyncSession, tenant_id: uuid.UUID, key: str | None, action: str, resource_id: uuid.UUID) -> TicketResponse | None:
    if not key:
        return None
    if len(key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency key is too long")
    receipt = await session.scalar(
        select(ClientMutation).where(ClientMutation.tenant_id == tenant_id, ClientMutation.idempotency_key == key)
    )
    if not receipt:
        return None
    if receipt.action != action or receipt.resource_id != resource_id:
        raise HTTPException(status_code=409, detail="Idempotency key was already used for another mutation")
    return TicketResponse.model_validate_json(receipt.response_json)

class TriageConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.broker: Any | None = None

    async def connect(self, tenant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[tenant_id].add(websocket)

    def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(tenant_id, set())
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(tenant_id, None)

    async def broadcast(self, tenant_id: str, event: dict[str, Any]) -> None:
        await self.broadcast_local(tenant_id, event)
        if self.broker:
            await self.broker.publish(tenant_id, event)

    async def broadcast_local(self, tenant_id: str, event: dict[str, Any]) -> None:
        dead_sockets: list[WebSocket] = []
        for websocket in list(self._connections.get(tenant_id, set())):
            try:
                await websocket.send_json(event)
            except Exception:
                dead_sockets.append(websocket)
        for websocket in dead_sockets:
            self.disconnect(tenant_id, websocket)

triage_manager = TriageConnectionManager()

async def broadcast_ticket_event(ticket: Ticket, event_type: str, payload: dict[str, Any], priority: str = "NORMAL") -> None:
    tenant_ids = {str(ticket.tenant_id), str(ticket.routed_tenant_id or ticket.tenant_id)}
    for tenant_id in tenant_ids:
        await triage_manager.broadcast(
            tenant_id,
            {"type": event_type, "tenant_id": tenant_id, "payload": payload, "priority": priority},
        )


async def create_appointment_notification(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    recipient_account_id: uuid.UUID | None,
    recipient_role: str,
    appointment: Appointment | None,
    ticket: Ticket,
    event_type: str,
    title: str,
    body: str,
    payload: dict[str, Any],
) -> Notification:
    notification = Notification(
        tenant_id=tenant_id,
        recipient_account_id=recipient_account_id,
        recipient_role=recipient_role,
        appointment_id=appointment.id if appointment else None,
        ticket_id=ticket.id,
        event_type=event_type,
        title=title,
        body=body,
        payload_json=json.dumps(payload, default=str),
    )
    session.add(notification)
    return notification


async def broadcast_appointment_event(tenant_id: uuid.UUID, event_type: str, payload: dict[str, Any], recipient_account_id: uuid.UUID | None = None) -> None:
    await triage_manager.broadcast(
        str(tenant_id),
        {"type": event_type, "tenant_id": str(tenant_id), "recipient_account_id": str(recipient_account_id) if recipient_account_id else None, "payload": payload, "priority": "NORMAL"},
    )
async def enforce_rate_limit(request: Request, scope: str, limit: int, identity: str | None = None) -> None:
    client_identity = identity or (request.client.host if request.client else "unknown")
    if not await request.app.state.redis.allow(scope, client_identity, limit):
        raise HTTPException(status_code=429, detail="Too many requests; please try again shortly", headers={"Retry-After": "60"})

def _build_profile(account: AuthAccount) -> AuthProfileResponse:
    title = "Dr. " if account.role == "specialist" else ""
    return AuthProfileResponse(
        id=str(account.id), role=account.role, tenant_id=str(account.tenant_id), phone=account.phone,
        email=account.email, first_name=account.first_name, last_name=account.last_name,
        full_name=f"{title}{account.first_name} {account.last_name}", specialty=account.specialty,
        card_number=account.card_number, subtitle=f"{account.role.title()} portal",
        date_of_birth=account.date_of_birth, gender=account.gender, state=account.state, lga=account.lga,
        emergency_contact=account.emergency_contact, hmo_provider=account.hmo_provider,
        blood_group=account.blood_group, genotype=account.genotype,
        known_allergies=account.known_allergies, current_medications=account.current_medications,
        created_at=account.created_at, card_valid_from=account.created_at,
        card_valid_until=account.created_at + timedelta(days=365 * 5) if account.card_number else None,
        locked_fields=[],
    )

def _set_session_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {"httponly": True, "secure": settings.auth_cookie_secure, "samesite": settings.auth_cookie_samesite, "path": "/"}
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.auth_access_minutes * 60, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=settings.auth_refresh_days * 86400, **common)

def _set_role_cookie(response: Response, role: str) -> None:
    response.set_cookie("synaptiverse_role", role, max_age=settings.auth_refresh_days * 86400, httponly=True, secure=settings.auth_cookie_secure, samesite=settings.auth_cookie_samesite, path="/")

async def _login_account(account: AuthAccount, response: Response, session: AsyncSession) -> AuthSessionResponse:
    issued = await create_session(session, account)
    await session.commit()
    _set_session_cookies(response, issued.access_token, issued.refresh_token)
    _set_role_cookie(response, account.role)
    return AuthSessionResponse(**_build_profile(account).model_dump(), access_expires_at=issued.session.access_expires_at)

async def get_db(request: Request) -> AsyncSession:
    session_factory: Any = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def require_account(request: Request, session: AsyncSession) -> AuthAccount:
    token = request.cookies.get(ACCESS_COOKIE)
    authenticated = await account_for_access_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    account = authenticated[0]
    session.info["tenant_id"] = str(account.tenant_id)
    if session.bind and session.bind.dialect.name == "postgresql":
        await session.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": str(account.tenant_id)})
    return account

async def require_roles(request: Request, session: AsyncSession, allowed: set[str]) -> AuthAccount:
    account = await require_account(request, session)
    if account.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient role permissions")
    return account

def public_tenant_id() -> str:
    return settings.default_tenant_id

async def tenant_control(session: AsyncSession, tenant_id: uuid.UUID, name: str, default: bool) -> bool:
    record = await session.scalar(select(OperationalRecord).where(OperationalRecord.tenant_id == tenant_id, OperationalRecord.entity == "system", OperationalRecord.resource == "settings", OperationalRecord.title == name))
    return default if not record else record.status == "ENABLED"

@router.websocket("/ws/triage")
@router.websocket("/ws/notifications")
async def triage_websocket(websocket: WebSocket) -> None:
    token = websocket.cookies.get(ACCESS_COOKIE)
    async with websocket.app.state.session_factory() as session:
        authenticated = await account_for_access_token(session, token) if token else None
    if not authenticated:
        await websocket.close(code=4401, reason="Authentication required")
        return
    tenant_key = str(authenticated[0].tenant_id)
    await triage_manager.connect(tenant_key, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        triage_manager.disconnect(tenant_key, websocket)

@router.post("/auth/{role}/login", response_model=AuthSessionResponse)
async def login(role: str, payload: AuthLoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthSessionResponse:
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    if role not in {"patient", "specialist"}:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    identifier = (payload.phone or payload.email or "").strip().lower()
    if not identifier or not payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    account = await find_account(session, role, identifier, uuid.UUID(settings.default_tenant_id))
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return await _login_account(account, response, session)

@router.post("/auth/staff/pin-login", response_model=AuthSessionResponse)
async def pin_login(payload: PinLoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthSessionResponse:
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    identifier = f"uyo-family:{payload.role}"
    account = await find_account(session, payload.role, identifier, uuid.UUID(settings.default_tenant_id))
    if not account or not verify_password(payload.pin, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid role or PIN")
    return await _login_account(account, response, session)

@router.post("/auth/hospital/account-login", response_model=AuthSessionResponse)
async def hospital_login(payload: HospitalLoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthSessionResponse:
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    identifier = f"{payload.hospital_code.strip().lower()}:{payload.role}"
    account = await find_account(session, payload.role, identifier, uuid.UUID(settings.default_tenant_id))
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid hospital credentials")
    return await _login_account(account, response, session)

@router.get("/auth/{role}/me", response_model=AuthProfileResponse)
async def get_current_profile(role: str, request: Request) -> AuthProfileResponse:
    async with request.app.state.session_factory() as session:
        token = request.cookies.get(ACCESS_COOKIE)
        authenticated = await account_for_access_token(session, token) if token else None
        if not authenticated or authenticated[0].role != role:
            raise HTTPException(status_code=401, detail="Authentication required")
        return _build_profile(authenticated[0])

@router.post("/auth/refresh", response_model=AuthRefreshResponse)
async def refresh_auth(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthRefreshResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    authenticated = await session_for_refresh_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Refresh session expired")
    account, previous = authenticated
    previous.revoked_at = utc_now()
    issued = await create_session(session, account)
    await session.commit()
    _set_session_cookies(response, issued.access_token, issued.refresh_token)
    return AuthRefreshResponse(access_expires_at=issued.session.access_expires_at)

@router.post("/auth/logout", status_code=204)
async def logout_auth(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> Response:
    token = request.cookies.get(REFRESH_COOKIE)
    authenticated = await session_for_refresh_token(session, token) if token else None
    if authenticated:
        authenticated[1].revoked_at = utc_now()
        await session.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie("synaptiverse_role", path="/")
    response.status_code = 204
    return response

@router.get("/hospital/me", response_model=AuthProfileResponse)
async def hospital_profile(request: Request, session: AsyncSession = Depends(get_db)) -> AuthProfileResponse:
    account = await require_roles(request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"})
    if account.role not in {"doctor", "nurse", "hospital_admin", "admin"}:
        raise HTTPException(status_code=403, detail="Hospital staff access required")
    return _build_profile(account)

@router.get("/hospital/waiting-room")
async def hospital_waiting_room(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "nurse", "hospital_admin", "admin"})
    result = await session.execute(
        select(Ticket)
        .where(ticket_visible_to_tenant(account.tenant_id), Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]))
        .order_by(Ticket.created_at.asc())
    )
    tickets = list(result.scalars().all())
    now_serving_ticket = next((ticket for ticket in reversed(tickets) if ticket.queue_status == "BEING_SEEN"), None)
    urgency_order = {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}
    queued = sorted(
        (ticket for ticket in tickets if ticket.queue_status == "QUEUED"),
        key=lambda ticket: (urgency_order.get(ticket.urgency_level, 3), ticket.created_at),
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
        row = departments.setdefault(name, {"name": name, "waiting": 0, "being_seen": 0, "resolved": 0})
        row["being_seen" if ticket.queue_status == "BEING_SEEN" else "waiting"] += 1
    return {
        "now_serving": now_serving,
        "up_next": [
            {"id": str(ticket.id), "ticket_number": ticket.ticket_number, "room_label": ticket.assigned_specialty or "Front Desk"}
            for ticket in queued[:4]
        ],
        "departments": list(departments.values()),
    }

@router.get("/hospital/settings")
async def hospital_settings(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "nurse", "hospital_admin", "admin"})
    tenant = await session.get(Tenant, account.tenant_id)
    staff = list((await session.execute(select(AuthAccount).where(AuthAccount.tenant_id == account.tenant_id, AuthAccount.role.in_(["doctor", "nurse", "hospital_admin", "admin"])))).scalars().all())
    return {"facility_name": tenant.name if tenant else "Hospital", "intake_paused": not await tenant_control(session, account.tenant_id, "intake_enabled", True), "sms_route": "SIGNED_WEBHOOK", "whatsapp_enabled": await tenant_control(session, account.tenant_id, "whatsapp_enabled", True), "staff": [{"id": str(row.id), "name": f"{row.first_name} {row.last_name}", "role": row.role, "scope": "Tenant"} for row in staff]}

@router.patch("/hospital/settings")
async def update_hospital_settings(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    payload = await request.json()
    changes = {"intake_enabled": not bool(payload["intake_paused"])} if "intake_paused" in payload else {}
    if "whatsapp_enabled" in payload:
        changes["whatsapp_enabled"] = bool(payload["whatsapp_enabled"])
    for name, enabled in changes.items():
        record = await session.scalar(select(OperationalRecord).where(OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == "system", OperationalRecord.resource == "settings", OperationalRecord.title == name).with_for_update())
        if record:
            record.status = "ENABLED" if enabled else "DISABLED"
            record.updated_at = utc_now()
        else:
            session.add(OperationalRecord(tenant_id=account.tenant_id, entity="system", resource="settings", title=name, description="Tenant runtime control", status="ENABLED" if enabled else "DISABLED"))
    await write_audit_log(session, AuditAction.KILL_SWITCH_TOGGLED if "intake_enabled" in changes else AuditAction.TENANT_SETTINGS_CHANGED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(account.tenant_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="TenantSettings", metadata={"controls": list(changes)})
    await session.commit()
    return await hospital_settings(request, session)

@router.get("/tickets", response_model=list[TicketResponse])
async def list_tickets(request: Request, session: AsyncSession = Depends(get_db)) -> list[TicketResponse]:
    account = await require_account(request, session)
    query = select(Ticket)
    if account.role == "patient":
        if not account.phone:
            return []
        query = query.where(Ticket.customer_phone == account.phone)
    elif account.role in {"specialist", "doctor", "nurse", "hospital_admin", "admin"}:
        query = query.where(ticket_visible_to_tenant(account.tenant_id))
    else:
        raise HTTPException(status_code=403, detail="Queue access not permitted")
    result = await session.execute(query.order_by(Ticket.created_at.desc()))
    tickets = result.scalars().all()
    if account.role == "patient":
        await write_audit_log(
            session,
            AuditAction.PATIENT_RECORD_VIEWED,
            actor_id=str(account.id),
            actor_type="PATIENT",
            tenant_id=str(account.tenant_id),
            ip_address=request.client.host if request.client else "127.0.0.1",
            resource_type="TicketCollection",
            metadata={"record_count": len(tickets)},
        )
        await session.commit()
    return [build_ticket_response(ticket) for ticket in tickets]

async def persist_ticket(
    payload: TicketCreate,
    request: Request,
    session: AsyncSession,
    clinical_route: Any,
    target_tenant_id: uuid.UUID | None = None,
    routed_tenant_id: uuid.UUID | None = None,
    patient_latitude: float | None = None,
    patient_longitude: float | None = None,
    route_distance_km: float | None = None,
) -> TicketResponse:
    tenant_uuid = target_tenant_id or uuid.UUID(public_tenant_id())
    routed_uuid = routed_tenant_id or tenant_uuid
    tenant_id = str(tenant_uuid)
    await apply_tenant_context(session, tenant_uuid)
    ticket_number = f"SV-{datetime.now(UTC).strftime('%Y-%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    ticket = Ticket(
        tenant_id=tenant_uuid,
        ticket_number=ticket_number,
        customer_phone=payload.customer_phone,
        raw_intake_text=payload.raw_intake_text.strip(),
        extracted_symptoms=json.dumps(clinical_route.symptom_ids),
        account_group_phone=payload.account_group_phone,
        channel=payload.channel,
        urgency_level=clinical_route.derived_urgency,
        matched_condition_id=clinical_route.condition_id,
        assigned_specialty=clinical_route.target_specialty,
        queue_status="QUEUED",
        appointment_slot=payload.appointment_slot,
        patient_latitude=patient_latitude,
        patient_longitude=patient_longitude,
        routed_tenant_id=routed_uuid,
        route_distance_km=route_distance_km,
    )
    session.add(ticket)
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.TICKET_CREATED,
        actor_id=None,
        actor_type="SYSTEM",
        tenant_id=tenant_id,
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Ticket",
        resource_id=str(ticket.id),
        metadata={"channel": payload.channel, "customer_phone": payload.customer_phone},
    )
    await session.commit()
    ticket_response = build_ticket_response(ticket)
    await broadcast_ticket_event(ticket, "ticket.created", ticket_response.model_dump())
    return ticket_response

@router.post("/tickets", response_model=TicketResponse, status_code=201)
async def create_ticket(payload: TicketCreate, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    await enforce_rate_limit(request, "public-intake", settings.public_intake_rate_limit, payload.customer_phone)
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    if not await tenant_control(session, tenant_id, "intake_enabled", True):
        raise HTTPException(status_code=503, detail="Clinic intake is temporarily paused")
    clinical_route = await request.app.state.knowledge_graph.route(payload.raw_intake_text)
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
            Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]),
        )
        .order_by(Ticket.created_at.desc())
    )
    active_ticket = result.scalars().first()
    channel_name = "WHATSAPP" if normalized_channel == "WHATSAPP" else "SMS"

    if active_ticket and payload.intent is None:
        menu = [
            ChannelMenuOption(id="CONTINUE_EXISTING", title="Continue existing visit", description=f"Use ticket {active_ticket.ticket_number}."),
            ChannelMenuOption(id="REGISTER_NEW_PATIENT", title="Register a new patient", description="Create a separate ticket linked to this shared phone."),
            ChannelMenuOption(id="BOOK_APPOINTMENT", title="Book an appointment", description="Show the next available provider times."),
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
            raise HTTPException(status_code=404, detail="No active visit for this phone")
        return ChannelIntakeResponse(
            action="CONTINUE_EXISTING",
            channel=channel_name,
            message=f"Continuing ticket {active_ticket.ticket_number}.",
            active_ticket_id=active_ticket.id,
            account_group_phone=active_ticket.account_group_phone or payload.customer_phone,
        )

    if payload.intent == "BOOK_APPOINTMENT":
        slot_rows = (await session.execute(
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
        )).all()
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
            message="Select an available appointment time." if slot_menu else "No appointment slots are currently available.",
            active_ticket_id=active_ticket.id if active_ticket else None,
            account_group_phone=payload.customer_phone,
            menu=slot_menu,
        )

    if payload.intent == "CONFIRM_APPOINTMENT":
        if not active_ticket or not payload.slot_id:
            raise HTTPException(status_code=422, detail="An active ticket and selected slot are required")
        booked = await book_appointment(
            AppointmentCreate(ticket_id=active_ticket.id, slot_id=payload.slot_id, customer_phone=payload.customer_phone),
            request,
            session,
        )
        return ChannelIntakeResponse(
            action="APPOINTMENT_BOOKED",
            channel=channel_name,
            message=f"Appointment confirmed for {booked.starts_at.strftime('%a %d %b at %H:%M')} with {booked.provider_name}.",
            active_ticket_id=active_ticket.id,
            account_group_phone=active_ticket.account_group_phone or payload.customer_phone,
        )

    if payload.intent == "CANCEL_APPOINTMENT":
        appointment = await session.scalar(
            select(Appointment)
            .where(Appointment.tenant_id == tenant_id, Appointment.customer_phone == payload.customer_phone, Appointment.status == "BOOKED")
            .order_by(Appointment.created_at.desc())
            .with_for_update()
        )
        if not appointment:
            raise HTTPException(status_code=404, detail="No active appointment for this phone")
        slot = await session.scalar(select(ProviderSlot).where(ProviderSlot.id == appointment.slot_id).with_for_update())
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
        raise HTTPException(status_code=422, detail="Describe the patient's main concern")

    ticket_payload = TicketCreate(
        customer_phone=payload.customer_phone,
        raw_intake_text=payload.raw_intake_text,
        channel=channel_name,
        account_group_phone=payload.customer_phone if payload.intent == "REGISTER_NEW_PATIENT" else None,
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
    return {"sms": [{"id": key, "body": value, "max_segments": 2} for key, value in SMS_TEMPLATES.items()]}

@router.get("/webhooks/whatsapp")
async def verify_whatsapp_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")
    if mode != "subscribe" or token != settings.whatsapp_verify_token:
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return Response(content=challenge, media_type="text/plain")

@router.post("/webhooks/{channel}")
async def channel_webhook(channel: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    normalized_channel = channel.lower()
    if normalized_channel not in {"whatsapp", "sms"}:
        raise HTTPException(status_code=404, detail="Channel not supported")
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256") or request.headers.get("x-synaptiverse-signature")
    if not valid_signature(body, signature, settings.channel_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        provider_event = normalize_webhook(normalized_channel, json.loads(body))
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=422, detail="Unsupported webhook payload") from error
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    message_id = str(provider_event.get("message_id") or uuid.uuid4())
    if provider_event.get("status"):
        record = await session.scalar(select(OperationalRecord).where(OperationalRecord.tenant_id == tenant_id, OperationalRecord.entity == normalized_channel, OperationalRecord.resource == "messages", OperationalRecord.title == message_id).order_by(OperationalRecord.created_at.desc()))
        if record:
            record.status = str(provider_event["status"]).upper()
            record.updated_at = utc_now()
        else:
            session.add(OperationalRecord(tenant_id=tenant_id, entity=normalized_channel, resource="messages", title=message_id, description="Provider delivery receipt", status=str(provider_event["status"]).upper()))
        await session.commit()
        return {"accepted": True, "message_id": message_id, "delivery_status": str(provider_event["status"]).upper()}
    text_value = str(provider_event.get("text") or "").strip()
    intent = provider_event.get("intent") or intent_from_text(text_value)
    payload = ChannelIntakeRequest(
        customer_phone=str(provider_event.get("from") or ""),
        raw_intake_text=text_value if not intent else None,
        intent=intent,
        slot_id=provider_event.get("slot_id"),
    )
    result = await channel_intake(normalized_channel, payload, request, session)
    session.add(OperationalRecord(tenant_id=tenant_id, entity=normalized_channel, resource="messages", title=message_id, description=result.message, status="QUEUED"))
    await session.commit()
    return {"accepted": True, "message_id": message_id, "reply": result.model_dump(mode="json")}

@router.get("/public/platform-stats")
async def public_platform_stats(session: AsyncSession = Depends(get_db)) -> dict[str, int]:
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    ticket_count = await session.scalar(select(func.count(Ticket.id)).where(Ticket.tenant_id == tenant_id))
    active_count = await session.scalar(
        select(func.count(Ticket.id)).where(Ticket.tenant_id == tenant_id, Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]))
    )
    return {"patients_routed": int(ticket_count or 0), "active_visits": int(active_count or 0), "channels_connected": 3, "clinic_regions": 2}

@router.post("/public/triage-preview")
async def public_triage_preview(request: Request) -> dict[str, Any]:
    await enforce_rate_limit(request, "public-triage-preview", settings.public_intake_rate_limit)
    payload = await request.json()
    symptom_text = str(payload.get("symptom_description") or "").strip()
    if len(symptom_text) < 3:
        raise HTTPException(status_code=422, detail="Describe the symptoms in a little more detail")
    clinical_route = await request.app.state.knowledge_graph.route(symptom_text)
    urgency = clinical_route.derived_urgency
    timing = "Seek emergency care now" if urgency == "CRITICAL" else "See a clinician today" if urgency == "URGENT" else "Book the next available visit"
    return {
        "condition_name": clinical_route.condition_id.replace("_", " ").title(),
        "possible_illness": possible_illness_for_route(clinical_route.condition_id, clinical_route.symptom_ids),
        "diagnosis_disclaimer": "This is not a diagnosis. A qualified clinician must confirm what illness you have.",
        "urgency": urgency,
        "specialty": clinical_route.target_specialty,
        "recommended_timing": timing,
        "severity": severity_for_urgency(urgency),
        "severity_label": severity_for_urgency(urgency).title(),
        "matched_symptoms": clinical_route.symptom_ids,
        "disclaimer": "This preview is informational and does not replace assessment by a qualified clinician.",
    }

@router.get("/public/pricing")
async def public_pricing() -> dict[str, Any]:
    return {"plans": [
        {"id": "pilot", "name": "Clinic Pilot", "price_label": "Let's talk", "description": "Queue, triage, patient tickets, and onboarding for one facility.", "cta_href": "/book-demo"},
        {"id": "network", "name": "Hospital Network", "price_label": "Custom", "description": "Multi-department workflows, scheduling, channels, and analytics.", "cta_href": "/book-demo"},
        {"id": "public", "name": "Public Health", "price_label": "Partnership", "description": "State-wide coordination and reporting for care networks.", "cta_href": "/book-demo"},
    ]}

@router.get("/public/blog-posts")
async def public_blog_posts() -> list[dict[str, str]]:
    return [
        {"id": "uyo-pilot", "category": "Clinic Operations", "title": "Reducing queue uncertainty in busy outpatient clinics", "excerpt": "How shared intake and live tickets improve the patient arrival experience."},
        {"id": "shared-phone", "category": "Access", "title": "Designing healthcare workflows for shared family phones", "excerpt": "Protecting patient identity without blocking low-bandwidth access."},
        {"id": "human-triage", "category": "Clinical Safety", "title": "Why automated triage still needs a human overtake control", "excerpt": "Supporting nurses when real-world urgency changes faster than software."},
    ]

@router.get("/public/testimonials")
async def public_testimonials() -> list[dict[str, str]]:
    return [
        {"id": "demo-1", "initials": "IA", "name": "Demo Clinic Lead", "role": "Uyo pilot persona", "quote": "One queue view gives our front desk and nurses the same operational picture."},
        {"id": "demo-2", "initials": "BO", "name": "Demo Medical Director", "role": "Lagos pilot persona", "quote": "The live ticket makes waiting clearer for patients without exposing clinical details."},
    ]

@router.post("/public/demo-requests", response_model=DemoRequestResponse, status_code=201)
async def create_demo_request(payload: DemoRequestCreate, session: AsyncSession = Depends(get_db)) -> DemoRequestResponse:
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    lead = DemoRequest(tenant_id=tenant_id, **payload.model_dump())
    session.add(lead)
    await session.commit()
    return DemoRequestResponse(id=lead.id, message="Thanks — your demo request has been received.")

@router.patch("/tickets/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    account = await require_roles(request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"})
    tenant_id = str(account.tenant_id)
    resource_id = uuid.UUID(ticket_id)
    idempotency_key = request.headers.get("x-idempotency-key")
    replay = await replayed_mutation(session, account.tenant_id, idempotency_key, "TICKET_ESCALATE", resource_id)
    if replay:
        return replay
    ticket = await session.scalar(select(Ticket).where(Ticket.id == resource_id, ticket_visible_to_tenant(account.tenant_id)).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replay = await replayed_mutation(session, account.tenant_id, idempotency_key, "TICKET_ESCALATE", resource_id)
    if replay:
        return replay
    expected_header = request.headers.get("x-expected-version")
    try:
        expected_version = int(expected_header) if expected_header else None
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Expected version must be an integer") from error
    if expected_version is not None and ticket.version != expected_version:
        raise HTTPException(status_code=409, detail={"message": "Ticket changed on another device", "current": build_ticket_response(ticket).model_dump(mode="json")})
    ticket.urgency_level = "CRITICAL"
    ticket.is_manually_escalated = True
    ticket.queue_status = "QUEUED"
    ticket.version += 1
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.TICKET_ESCALATED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=tenant_id,
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Ticket",
        resource_id=ticket_id,
        metadata={"manual_escalation": True},
    )
    response = build_ticket_response(ticket)
    if idempotency_key:
        session.add(ClientMutation(tenant_id=account.tenant_id, idempotency_key=idempotency_key, action="TICKET_ESCALATE", resource_id=resource_id, response_json=response.model_dump_json()))
    await session.commit()
    await broadcast_ticket_event(ticket, "ticket.escalated", response.model_dump(), "HIGH")
    return response

@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(ticket_id: str, payload: TicketUpdate, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    account = await require_roles(request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"})
    tenant_id = str(account.tenant_id)
    resource_id = uuid.UUID(ticket_id)
    idempotency_key = request.headers.get("x-idempotency-key")
    replay = await replayed_mutation(session, account.tenant_id, idempotency_key, "TICKET_UPDATE", resource_id)
    if replay:
        return replay
    ticket = await session.scalar(select(Ticket).where(Ticket.id == resource_id, ticket_visible_to_tenant(account.tenant_id)).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replay = await replayed_mutation(session, account.tenant_id, idempotency_key, "TICKET_UPDATE", resource_id)
    if replay:
        return replay
    if payload.expected_version is not None and ticket.version != payload.expected_version:
        raise HTTPException(status_code=409, detail={"message": "Ticket changed on another device", "current": build_ticket_response(ticket).model_dump(mode="json")})
    if payload.queue_status is not None:
        ticket.queue_status = payload.queue_status
    if payload.urgency_level is not None:
        ticket.urgency_level = payload.urgency_level
    if payload.is_manually_escalated is not None:
        ticket.is_manually_escalated = payload.is_manually_escalated
    ticket.version += 1
    await session.flush()
    await write_audit_log(
        session,
        AuditAction.TICKET_STATUS_CHANGED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=tenant_id,
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="Ticket",
        resource_id=ticket_id,
    )
    response = build_ticket_response(ticket)
    if idempotency_key:
        session.add(ClientMutation(tenant_id=account.tenant_id, idempotency_key=idempotency_key, action="TICKET_UPDATE", resource_id=resource_id, response_json=response.model_dump_json()))
    await session.commit()
    await broadcast_ticket_event(ticket, "ticket.updated", response.model_dump())
    return response

@router.get("/appointments/slots", response_model=list[SlotResponse])
async def list_slots(request: Request, session: AsyncSession = Depends(get_db)) -> list[SlotResponse]:
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    result = await session.execute(
        select(ProviderSlot, Provider)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(ProviderSlot.tenant_id == tenant_id, Provider.is_active.is_(True))
        .order_by(ProviderSlot.starts_at.asc())
    )
    return [
        SlotResponse(
            id=slot.id, tenant_id=slot.tenant_id, provider_name=provider.full_name,
            specialty=provider.specialty, room_label=provider.room_label,
            starts_at=slot.starts_at, ends_at=slot.ends_at, is_locked=slot.is_locked,
            lock_reason=slot.lock_reason, is_booked=slot.is_booked,
        )
        for slot, provider in result.all()
    ]

@router.patch("/appointments/slots/{slot_id}/lock")
async def lock_slot(slot_id: str, payload: SlotLockRequest, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"})
    slot = await session.scalar(
        select(ProviderSlot).where(ProviderSlot.id == uuid.UUID(slot_id), ProviderSlot.tenant_id == account.tenant_id).with_for_update()
    )
    if not slot:
        raise HTTPException(status_code=404, detail="Appointment slot not found")
    if slot.is_booked and payload.is_locked:
        raise HTTPException(status_code=409, detail="Booked slots cannot be blocked")
    slot.is_locked = payload.is_locked
    slot.lock_reason = payload.reason if payload.is_locked else None
    await session.commit()
    await triage_manager.broadcast(str(account.tenant_id), {"type": "appointment.updated", "tenant_id": str(account.tenant_id), "payload": {"slot_id": slot_id, "is_locked": slot.is_locked, "lock_reason": slot.lock_reason}, "priority": "NORMAL"})
    return {"ok": True, "slot_id": slot_id, "is_locked": slot.is_locked, "lock_reason": slot.lock_reason}

async def appointment_response(session: AsyncSession, appointment: Appointment) -> AppointmentResponse:
    slot, provider = (await session.execute(
        select(ProviderSlot, Provider).join(Provider, Provider.id == ProviderSlot.provider_id).where(ProviderSlot.id == appointment.slot_id)
    )).one()
    return AppointmentResponse(
        id=appointment.id,
        tenant_id=appointment.tenant_id,
        hospital_id=appointment.hospital_id,
        ticket_id=appointment.ticket_id,
        doctor_id=appointment.doctor_id,
        specialty_id=appointment.specialty_id,
        slot_id=appointment.slot_id,
        customer_phone=appointment.customer_phone,
        urgency=appointment.urgency,
        status=appointment.status,
        provider_name=provider.full_name,
        specialty=provider.specialty,
        room_label=provider.room_label,
        starts_at=appointment.starts_at or slot.starts_at,
        ends_at=appointment.ends_at or slot.ends_at,
    )
@router.post("/appointments", response_model=AppointmentResponse, status_code=201)
async def book_appointment(payload: AppointmentCreate, request: Request, session: AsyncSession = Depends(get_db)) -> AppointmentResponse:
    requester = await account_for_access_token(session, request.cookies.get(ACCESS_COOKIE)) if request.cookies.get(ACCESS_COOKIE) else None
    owner_tenant_id = requester.tenant_id if requester and requester.role == "patient" else uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, owner_tenant_id)
    ticket = await session.scalar(select(Ticket).where(Ticket.id == payload.ticket_id, Ticket.customer_phone == payload.customer_phone).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found for this phone")
    destination_tenant_id = ticket_destination_id(ticket)
    specialty_id = ticket.assigned_specialty
    if not specialty_id:
        raise HTTPException(status_code=409, detail="Ticket has no triage specialty for doctor assignment")
    existing = await session.scalar(select(Appointment).where(Appointment.ticket_id == ticket.id, Appointment.status == "BOOKED"))
    if existing:
        raise HTTPException(status_code=409, detail="Ticket already has an appointment")

    await apply_tenant_context(session, destination_tenant_id)
    row = (await session.execute(
        select(ProviderSlot, Provider, AuthAccount, HospitalDoctorMembership)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .join(AuthAccount, AuthAccount.id == Provider.doctor_id)
        .join(
            HospitalDoctorMembership,
            (HospitalDoctorMembership.hospital_id == ProviderSlot.tenant_id)
            & (HospitalDoctorMembership.doctor_id == AuthAccount.id)
            & (HospitalDoctorMembership.specialty_id == Provider.specialty),
        )
        .where(
            ProviderSlot.id == payload.slot_id,
            ProviderSlot.tenant_id == destination_tenant_id,
            ProviderSlot.is_locked.is_(False),
            ProviderSlot.is_booked.is_(False),
            Provider.is_active.is_(True),
            Provider.specialty == specialty_id,
            AuthAccount.is_active.is_(True),
            AuthAccount.role.in_(["doctor", "specialist"]),
            HospitalDoctorMembership.is_active.is_(True),
            HospitalDoctorMembership.verification_status == "VERIFIED",
            HospitalDoctorMembership.employment_status == "ACTIVE",
            HospitalDoctorMembership.active_from <= ProviderSlot.starts_at,
            or_(HospitalDoctorMembership.active_until.is_(None), HospitalDoctorMembership.active_until >= ProviderSlot.starts_at),
        )
        .order_by(ProviderSlot.starts_at.asc(), Provider.full_name.asc())
        .with_for_update()
    )).first()

    if not row:
        ticket.queue_status = "AWAITING_CLINICAL_REVIEW"
        eligible_doctors = list((await session.execute(
            select(AuthAccount)
            .join(HospitalDoctorMembership, HospitalDoctorMembership.doctor_id == AuthAccount.id)
            .where(
                HospitalDoctorMembership.hospital_id == destination_tenant_id,
                HospitalDoctorMembership.specialty_id == specialty_id,
                HospitalDoctorMembership.is_active.is_(True),
                HospitalDoctorMembership.verification_status == "VERIFIED",
                HospitalDoctorMembership.employment_status == "ACTIVE",
                AuthAccount.is_active.is_(True),
            )
        )).scalars().all())
        recipients = eligible_doctors or [None]
        for recipient in recipients:
            await create_appointment_notification(
                session,
                tenant_id=destination_tenant_id,
                recipient_account_id=recipient.id if recipient else None,
                recipient_role="doctor" if recipient else "department_coordinator",
                appointment=None,
                ticket=ticket,
                event_type="appointment.reassignment_requested",
                title="Specialist review needed",
                body="No eligible verified doctor was available for the requested routed appointment slot.",
                payload={"ticket_id": str(ticket.id), "specialty_id": specialty_id, "hospital_id": str(destination_tenant_id)},
            )
        await session.commit()
        await broadcast_appointment_event(destination_tenant_id, "appointment.reassignment_requested", {"ticket_id": str(ticket.id), "specialty_id": specialty_id})
        raise HTTPException(status_code=409, detail="No eligible verified doctor is available at the routed hospital for this specialty and slot")

    slot, provider, doctor, membership = row
    day_start = datetime.combine(slot.starts_at.date(), time.min, tzinfo=slot.starts_at.tzinfo or UTC)
    day_end = day_start + timedelta(days=1)
    booked_count = await session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.hospital_id == destination_tenant_id,
            Appointment.doctor_id == doctor.id,
            Appointment.status == "BOOKED",
            Appointment.starts_at >= day_start,
            Appointment.starts_at < day_end,
        )
    )
    if (booked_count or 0) >= provider.max_daily_capacity:
        ticket.queue_status = "AWAITING_CLINICAL_REVIEW"
        await create_appointment_notification(
            session,
            tenant_id=destination_tenant_id,
            recipient_account_id=None,
            recipient_role="department_coordinator",
            appointment=None,
            ticket=ticket,
            event_type="appointment.reassignment_requested",
            title="Doctor capacity reached",
            body="The eligible doctor for this routed appointment has reached capacity.",
            payload={"ticket_id": str(ticket.id), "doctor_id": str(doctor.id), "specialty_id": specialty_id},
        )
        await session.commit()
        await broadcast_appointment_event(destination_tenant_id, "appointment.reassignment_requested", {"ticket_id": str(ticket.id), "doctor_id": str(doctor.id), "specialty_id": specialty_id})
        raise HTTPException(status_code=409, detail="Eligible doctor capacity has been reached at the routed hospital")

    slot.is_booked = True
    ticket.appointment_slot = slot.starts_at
    appointment = Appointment(
        tenant_id=destination_tenant_id,
        hospital_id=destination_tenant_id,
        ticket_id=ticket.id,
        doctor_id=doctor.id,
        specialty_id=membership.specialty_id,
        slot_id=slot.id,
        customer_phone=payload.customer_phone,
        urgency=ticket.urgency_level,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        status="BOOKED",
    )
    session.add(appointment)
    await session.flush()
    response_payload = {
        "appointment_id": str(appointment.id),
        "ticket_id": str(ticket.id),
        "patient_phone": ticket.customer_phone,
        "starts_at": slot.starts_at.isoformat(),
        "ends_at": slot.ends_at.isoformat(),
        "hospital_id": str(destination_tenant_id),
        "doctor_id": str(doctor.id),
        "specialty_id": membership.specialty_id,
        "urgency": ticket.urgency_level,
        "room_label": provider.room_label,
        "actions": ["view", "accept", "request_reassignment"],
    }
    await create_appointment_notification(
        session,
        tenant_id=destination_tenant_id,
        recipient_account_id=doctor.id,
        recipient_role="doctor",
        appointment=appointment,
        ticket=ticket,
        event_type="appointment.assigned",
        title="New appointment assigned",
        body=f"{membership.specialty_id} appointment at {provider.room_label}",
        payload=response_payload,
    )
    await create_appointment_notification(
        session,
        tenant_id=ticket.tenant_id,
        recipient_account_id=requester.id if requester and requester.role == "patient" else None,
        recipient_role="patient",
        appointment=appointment,
        ticket=ticket,
        event_type="appointment.created",
        title="Appointment confirmed",
        body="Your appointment has been confirmed at the routed hospital.",
        payload=response_payload,
    )
    await write_audit_log(session, AuditAction.APPOINTMENT_BOOKED, actor_id=None, actor_type="PATIENT", tenant_id=str(destination_tenant_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="Appointment", resource_id=str(appointment.id))
    await session.commit()
    await apply_tenant_context(session, destination_tenant_id)
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(destination_tenant_id, "appointment.assigned", response_payload, doctor.id)
    await broadcast_appointment_event(ticket.tenant_id, "appointment.created", response_payload, requester.id if requester and requester.role == "patient" else None)
    return response
@router.get("/appointments", response_model=list[AppointmentResponse])
async def staff_appointments(request: Request, session: AsyncSession = Depends(get_db)) -> list[AppointmentResponse]:
    account = await require_roles(request, session, {"specialist", "doctor", "nurse", "hospital_admin", "admin"})
    query = select(Appointment).where(Appointment.hospital_id == account.tenant_id, Appointment.status == "BOOKED")
    if account.role in {"doctor", "specialist"}:
        query = query.where(Appointment.doctor_id == account.id)
    result = await session.execute(query.order_by(Appointment.created_at.asc()))
    return [await appointment_response(session, appointment) for appointment in result.scalars().all()]
@router.get("/patient/appointments", response_model=list[AppointmentResponse])
async def patient_appointments(request: Request, session: AsyncSession = Depends(get_db)) -> list[AppointmentResponse]:
    account = await require_account(request, session)
    if account.role != "patient" or not account.phone:
        raise HTTPException(status_code=403, detail="Patient access required")
    ticket_rows = list((await session.execute(
        select(Ticket).where(Ticket.customer_phone == account.phone).order_by(Ticket.created_at.desc())
    )).scalars().all())
    ticket_ids = [ticket.id for ticket in ticket_rows]
    if not ticket_ids:
        return []
    appointments: list[Appointment] = []
    destination_ids = {ticket_destination_id(ticket) for ticket in ticket_rows}
    for destination_id in destination_ids:
        await apply_tenant_context(session, destination_id)
        result = await session.execute(
            select(Appointment)
            .where(Appointment.customer_phone == account.phone, Appointment.ticket_id.in_(ticket_ids))
            .order_by(Appointment.created_at.desc())
        )
        appointments.extend(result.scalars().all())
    appointments.sort(key=lambda appointment: appointment.created_at, reverse=True)
    return [await appointment_response(session, appointment) for appointment in appointments]

@router.patch("/patient/profile", response_model=AuthProfileResponse)
async def update_patient_profile(payload: PatientProfileUpdate, request: Request, session: AsyncSession = Depends(get_db)) -> AuthProfileResponse:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    updates = payload.model_dump(exclude_unset=True)
    full_name = updates.pop("full_name", None)
    if full_name:
        name_parts = full_name.strip().split(maxsplit=1)
        account.first_name = name_parts[0]
        account.last_name = name_parts[1] if len(name_parts) > 1 else ""
    for field, value in updates.items():
        setattr(account, field, value.strip() if isinstance(value, str) else value)
    if "phone" in updates and updates["phone"]:
        account.identifier = updates["phone"]
    await session.commit()
    return _build_profile(account)

@router.patch("/patient/card-details", response_model=AuthProfileResponse)
async def update_patient_card(payload: PatientCardUpdate, request: Request, session: AsyncSession = Depends(get_db)) -> AuthProfileResponse:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value.strip() if isinstance(value, str) else value)
    await session.commit()
    return _build_profile(account)

@router.get("/patient/history")
async def patient_history(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    if account.role != "patient" or not account.phone:
        raise HTTPException(status_code=403, detail="Patient access required")
    tickets = (await session.execute(
        select(Ticket).where(Ticket.customer_phone == account.phone).order_by(Ticket.created_at.desc())
    )).scalars().all()
    appointment_rows = (await session.execute(
        select(Appointment, ProviderSlot, Provider)
        .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(Appointment.tenant_id == account.tenant_id, Appointment.customer_phone == account.phone)
        .order_by(Appointment.created_at.desc())
    )).all()
    events = [
        {"id": str(ticket.id), "type": "TRIAGE", "title": f"Triage ticket {ticket.ticket_number}", "summary": ticket.raw_intake_text, "status": ticket.urgency_level, "created_at": ticket.created_at, "tone": "rose" if ticket.urgency_level == "CRITICAL" else "sky"}
        for ticket in tickets
    ]
    events.extend(
        {"id": str(appointment.id), "type": "APPOINTMENT", "title": f"Appointment with {provider.full_name}", "provider_name": provider.full_name, "facility_name": provider.room_label, "status": appointment.status, "created_at": appointment.created_at, "tone": "violet"}
        for appointment, _slot, provider in appointment_rows
    )
    return sorted(events, key=lambda event: event["created_at"], reverse=True)

@router.get("/patient/dashboard")
async def patient_dashboard(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient" or not account.phone:
        raise HTTPException(status_code=403, detail="Patient access required")
    tickets = (await session.execute(
        select(Ticket).where(Ticket.customer_phone == account.phone).order_by(Ticket.created_at.desc())
    )).scalars().all()
    next_slot = (await session.execute(
        select(ProviderSlot).join(Appointment, Appointment.slot_id == ProviderSlot.id).where(
            Appointment.tenant_id == account.tenant_id, Appointment.customer_phone == account.phone,
            Appointment.status == "BOOKED", ProviderSlot.starts_at >= utc_now(),
        ).order_by(ProviderSlot.starts_at.asc()).limit(1)
    )).scalar_one_or_none()
    active = [ticket for ticket in tickets if ticket.queue_status != "RESOLVED"]
    queue = await patient_queue(request, session)
    return {
        "stats": {
            "active_tickets": len(active),
            "next_appointment": next_slot.starts_at.isoformat() if next_slot else "None scheduled",
            "queue_position": queue["queue_position"] if queue else "—",
            "health_card_status": "Active" if account.card_number else "Not issued",
        },
        "activity": [{"id": str(ticket.id), "title": f"{ticket.ticket_number} · {ticket.queue_status.replace('_', ' ').title()}", "created_at": ticket.created_at.isoformat()} for ticket in tickets[:5]],
        "health_tip": {"title": "Prepare for your visit", "body": "Keep your ticket number available and bring a list of current medications."},
    }

@router.patch("/appointments/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(appointment_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> AppointmentResponse:
    account = await require_account(request, session)
    appointment_query = select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    if account.role == "patient":
        appointment_query = appointment_query.where(Appointment.customer_phone == account.phone)
    else:
        appointment_query = appointment_query.where(Appointment.hospital_id == account.tenant_id)
        if account.role in {"doctor", "specialist"}:
            appointment_query = appointment_query.where(Appointment.doctor_id == account.id)
    appointment = await session.scalar(appointment_query.with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != "BOOKED":
        raise HTTPException(status_code=409, detail="Appointment is not active")
    slot = await session.scalar(select(ProviderSlot).where(ProviderSlot.id == appointment.slot_id).with_for_update())
    appointment.status = "CANCELLED"
    appointment.updated_at = utc_now()
    if slot:
        slot.is_booked = False
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = None
        await create_appointment_notification(session, tenant_id=appointment.hospital_id, recipient_account_id=appointment.doctor_id, recipient_role="doctor", appointment=appointment, ticket=ticket, event_type="appointment.cancelled", title="Appointment cancelled", body="An assigned appointment was cancelled.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id)})
    await write_audit_log(session, AuditAction.APPOINTMENT_CANCELLED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(appointment.hospital_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="Appointment", resource_id=str(appointment.id))
    await session.commit()
    await apply_tenant_context(session, appointment.hospital_id)
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(appointment.hospital_id, "appointment.cancelled", response.model_dump(), appointment.doctor_id)
    return response

@router.patch("/appointments/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(appointment_id: str, payload: AppointmentMoveRequest, request: Request, session: AsyncSession = Depends(get_db)) -> AppointmentResponse:
    account = await require_account(request, session)
    appointment_query = select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    if account.role == "patient":
        appointment_query = appointment_query.where(Appointment.customer_phone == account.phone)
    else:
        appointment_query = appointment_query.where(Appointment.hospital_id == account.tenant_id)
        if account.role in {"doctor", "specialist"}:
            appointment_query = appointment_query.where(Appointment.doctor_id == account.id)
    appointment = await session.scalar(appointment_query.with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status != "BOOKED":
        raise HTTPException(status_code=409, detail="Appointment is not active")
    slots = (await session.execute(select(ProviderSlot).where(ProviderSlot.id.in_([appointment.slot_id, payload.slot_id])).with_for_update())).scalars().all()
    slot_map = {slot.id: slot for slot in slots}
    old_slot, new_slot = slot_map.get(appointment.slot_id), slot_map.get(payload.slot_id)
    if not new_slot or new_slot.tenant_id != appointment.hospital_id:
        raise HTTPException(status_code=404, detail="New slot not found")
    provider = await session.scalar(select(Provider).where(Provider.id == new_slot.provider_id))
    if not provider or provider.doctor_id != appointment.doctor_id or provider.specialty != appointment.specialty_id:
        raise HTTPException(status_code=409, detail="New slot does not match the assigned doctor and specialty")
    if new_slot.is_locked or new_slot.is_booked:
        raise HTTPException(status_code=409, detail="New slot is no longer available")
    if old_slot:
        old_slot.is_booked = False
    new_slot.is_booked = True
    appointment.slot_id = new_slot.id
    appointment.starts_at = new_slot.starts_at
    appointment.ends_at = new_slot.ends_at
    appointment.updated_at = utc_now()
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = new_slot.starts_at
        await create_appointment_notification(session, tenant_id=appointment.hospital_id, recipient_account_id=appointment.doctor_id, recipient_role="doctor", appointment=appointment, ticket=ticket, event_type="appointment.rescheduled", title="Appointment rescheduled", body="An assigned appointment was rescheduled.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id), "starts_at": new_slot.starts_at.isoformat()})
    await write_audit_log(session, AuditAction.APPOINTMENT_RESCHEDULED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(appointment.hospital_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="Appointment", resource_id=str(appointment.id), metadata={"new_slot_id": str(new_slot.id)})
    await session.commit()
    await apply_tenant_context(session, appointment.hospital_id)
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(appointment.hospital_id, "appointment.rescheduled", response.model_dump(), appointment.doctor_id)
    return response
@router.post("/appointments/{appointment_id}/accept", response_model=AppointmentResponse)
async def accept_unassigned_appointment(appointment_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> AppointmentResponse:
    account = await require_roles(request, session, {"doctor", "specialist"})
    appointment = await session.scalar(select(Appointment).where(Appointment.id == uuid.UUID(appointment_id), Appointment.hospital_id == account.tenant_id).with_for_update())
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.doctor_id is not None:
        raise HTTPException(status_code=409, detail="Appointment has already been accepted")
    if appointment.status not in {"AWAITING_CLINICAL_REVIEW", "SPECIALIST_UNAVAILABLE"}:
        raise HTTPException(status_code=409, detail="Appointment is not awaiting doctor acceptance")
    slot, provider = (await session.execute(
        select(ProviderSlot, Provider)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(ProviderSlot.id == appointment.slot_id, ProviderSlot.tenant_id == appointment.hospital_id)
        .with_for_update()
    )).one()
    membership = await session.scalar(select(HospitalDoctorMembership).where(
        HospitalDoctorMembership.hospital_id == appointment.hospital_id,
        HospitalDoctorMembership.doctor_id == account.id,
        HospitalDoctorMembership.specialty_id == appointment.specialty_id,
        HospitalDoctorMembership.is_active.is_(True),
        HospitalDoctorMembership.verification_status == "VERIFIED",
        HospitalDoctorMembership.employment_status == "ACTIVE",
    ))
    if not membership or not account.is_active or provider.specialty != appointment.specialty_id or slot.is_locked or slot.is_booked:
        raise HTTPException(status_code=403, detail="Doctor is not eligible to accept this appointment")
    appointment.doctor_id = account.id
    appointment.status = "BOOKED"
    slot.is_booked = True
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = appointment.starts_at or slot.starts_at
        await create_appointment_notification(session, tenant_id=appointment.hospital_id, recipient_account_id=account.id, recipient_role="doctor", appointment=appointment, ticket=ticket, event_type="appointment.assigned", title="Appointment accepted", body="You accepted this appointment.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id)})
    await session.commit()
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(appointment.hospital_id, "appointment.assigned", response.model_dump(), account.id)
    return response
@router.get("/patient/queue")
async def patient_queue(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any] | None:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    result = await session.execute(
        select(Ticket)
        .where(
            Ticket.customer_phone == account.phone,
            Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]),
        )
        .order_by(Ticket.created_at.asc())
    )
    active_tickets = list(result.scalars().all())
    patient_ticket = next((ticket for ticket in active_tickets if ticket.queue_status == "BEING_SEEN"), active_tickets[0] if active_tickets else None)
    if not patient_ticket:
        return None
    destination_id = ticket_destination_id(patient_ticket)
    ahead_result = await session.execute(
        select(Ticket.id).where(
            ticket_destination_queue(destination_id),
            Ticket.queue_status == "QUEUED",
            Ticket.created_at < patient_ticket.created_at,
        )
    )
    return {
        "ticket_number": patient_ticket.ticket_number,
        "queue_position": len(ahead_result.scalars().all()) + 1 if patient_ticket.queue_status == "QUEUED" else 0,
        "queue_status": patient_ticket.queue_status,
    }

@router.post("/patient/triage")
async def patient_triage(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    payload = await request.json()
    symptom_text = (payload.get("symptom_description") or "").strip()
    if len(symptom_text) < 3:
        raise HTTPException(status_code=422, detail="Describe the symptoms in a little more detail")
    patient_latitude, patient_longitude = patient_coordinates_from_payload(payload)
    clinical_route = await request.app.state.knowledge_graph.route(symptom_text)
    facility_route = await select_nearest_eligible_hospital(session, patient_latitude, patient_longitude, clinical_route)
    if not facility_route:
        raise HTTPException(status_code=503, detail="No active registered hospital with coordinates is available for patient intake")
    ticket = await persist_ticket(
        TicketCreate(customer_phone=account.phone or "", raw_intake_text=symptom_text, channel="WEB"),
        request,
        session,
        clinical_route,
        account.tenant_id,
        facility_route.tenant.id,
        patient_latitude,
        patient_longitude,
        facility_route.distance_km,
    )
    slot_payload = None
    if facility_route.slot and facility_route.provider:
        slot = facility_route.slot
        provider = facility_route.provider
        slot_payload = {"slot_id": str(slot.id), "slot_start": slot.starts_at.isoformat(), "slot_end": slot.ends_at.isoformat(), "specialist_name": provider.full_name, "specialty": provider.specialty, "room_label": provider.room_label}
    return {
        "condition_name": clinical_route.condition_id.replace("_", " ").title(),
        "possible_illness": possible_illness_for_route(clinical_route.condition_id, clinical_route.symptom_ids),
        "diagnosis_disclaimer": "This is not a diagnosis. A qualified clinician must confirm what illness you have.",
        "urgency": clinical_route.derived_urgency,
        "specialty": clinical_route.target_specialty,
        "severity": severity_for_urgency(clinical_route.derived_urgency),
        "severity_label": severity_for_urgency(clinical_route.derived_urgency).title(),
        "severity_message": severity_message_for_urgency(clinical_route.derived_urgency),
        "messages": [f"I identified: {', '.join(clinical_route.symptom_ids) or 'no exact symptom match'}.", f"Routing source: {clinical_route.source}."],
        "nearest_clinic": {"tenant_id": str(facility_route.tenant.id), "clinic_name": facility_route.tenant.name, "address": facility_route.tenant.state_location, "distance_km": round(facility_route.distance_km, 2), "specialist_name": facility_route.provider.full_name if facility_route.provider else None, "match_basis": facility_route.match_basis},
        "appointment_slot": slot_payload,
        "ticket": {"id": str(ticket.id), "ticket_number": ticket.ticket_number},
    }

@router.get("/notifications")
async def notifications(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    stored_notifications = list((await session.execute(
        select(Notification)
        .where(
            Notification.tenant_id == account.tenant_id,
            or_(Notification.recipient_account_id == account.id, Notification.recipient_account_id.is_(None)),
        )
        .order_by(Notification.created_at.desc())
        .limit(20)
    )).scalars().all())
    rows = [
        {
            "id": str(notification.id),
            "recipient_type": notification.recipient_role.upper(),
            "recipient_id": str(notification.recipient_account_id) if notification.recipient_account_id else None,
            "title": notification.title,
            "body": notification.body or "",
            "is_read": notification.is_read,
            "ticket_id": str(notification.ticket_id) if notification.ticket_id else None,
            "appointment_id": str(notification.appointment_id) if notification.appointment_id else None,
            "type": notification.event_type,
            "created_at": notification.created_at,
        }
        for notification in stored_notifications
    ]
    ticket_query = select(Ticket)
    if account.role == "patient":
        ticket_query = ticket_query.where(Ticket.customer_phone == account.phone)
    else:
        ticket_query = ticket_query.where(ticket_visible_to_tenant(account.tenant_id))
    tickets = list((await session.execute(ticket_query.order_by(Ticket.created_at.desc()).limit(20))).scalars().all())
    marker_prefix = f"{account.id}:"
    markers = list((await session.execute(select(OperationalRecord).where(OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == "notification", OperationalRecord.resource == "read", OperationalRecord.title.like(f"{marker_prefix}%")))).scalars().all())
    read_ids = {marker.title.removeprefix(marker_prefix) for marker in markers}
    rows.extend({"id": str(ticket.id), "recipient_type": "PATIENT" if account.role == "patient" else "SPECIALIST", "recipient_id": str(account.id), "title": f"Queue update · {ticket.ticket_number}", "body": f"{ticket.queue_status.replace('_', ' ').title()} · {ticket.assigned_specialty or 'Front Desk'}", "is_read": str(ticket.id) in read_ids, "ticket_id": str(ticket.id), "urgency_level": ticket.urgency_level, "condition_name": ticket.matched_condition_id, "type": "QUEUE_UPDATE", "created_at": ticket.created_at} for ticket in tickets)
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)
async def mark_notification(session: AsyncSession, account: AuthAccount, ticket_id: str) -> None:
    title = f"{account.id}:{ticket_id}"
    exists = await session.scalar(select(OperationalRecord).where(OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == "notification", OperationalRecord.resource == "read", OperationalRecord.title == title))
    if not exists:
        session.add(OperationalRecord(tenant_id=account.tenant_id, entity="notification", resource="read", title=title, description="Notification read marker", status="READ"))

@router.patch("/notifications/read-all")
async def mark_all_notifications_read(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    account = await require_account(request, session)
    ticket_query = select(Ticket.id)
    if account.role == "patient":
        ticket_query = ticket_query.where(Ticket.customer_phone == account.phone)
    else:
        ticket_query = ticket_query.where(ticket_visible_to_tenant(account.tenant_id))
    ticket_ids = (await session.execute(ticket_query)).scalars().all()
    for ticket_id in ticket_ids:
        await mark_notification(session, account, str(ticket_id))
    await session.commit()
    return {"ok": True}

@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    account = await require_account(request, session)
    ticket_query = select(Ticket).where(Ticket.id == uuid.UUID(notification_id))
    if account.role == "patient":
        ticket_query = ticket_query.where(Ticket.customer_phone == account.phone)
    else:
        ticket_query = ticket_query.where(ticket_visible_to_tenant(account.tenant_id))
    ticket = await session.scalar(ticket_query)
    if not ticket:
        raise HTTPException(status_code=404, detail="Notification not found")
    await mark_notification(session, account, notification_id)
    await session.commit()
    return {"ok": True}

OPERATIONAL_RESOURCES = {
    "dashboard", "queue", "people", "doctors", "specialists", "appointments", "analytics",
    "notifications", "settings", "schedule", "patients", "visits", "vitals", "care-plans", "departments",
    "deliveries", "inventory", "prescriptions", "collections", "equipment", "requests", "results",
    "authorizations", "claims", "facilities", "members", "payments", "utilization", "reports", "surveillance", "messages",
}

SPECIALIST_RESOURCES = {"dashboard", "queue", "patients", "appointments", "schedule", "notes", "messages", "earnings", "notifications", "settings"}

async def require_specialist(request: Request, session: AsyncSession) -> AuthAccount:
    account = await require_account(request, session)
    if account.role != "specialist":
        raise HTTPException(status_code=403, detail="Specialist access required")
    return account

@router.get("/specialist/{resource}")
async def specialist_resource(resource: str, request: Request, assigned_only: bool = False, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if resource not in SPECIALIST_RESOURCES:
        raise HTTPException(status_code=404, detail="Specialist resource not found")
    account = await require_specialist(request, session)
    ticket_query = select(Ticket).where(ticket_visible_to_tenant(account.tenant_id))
    if assigned_only:
        ticket_query = ticket_query.where(Ticket.assigned_specialist_id == account.id)
    tickets = list((await session.execute(ticket_query.order_by(Ticket.created_at.desc()))).scalars().all())
    providers = list((await session.execute(
        select(Provider).where(Provider.tenant_id == account.tenant_id, Provider.specialty == (account.specialty or "General Medicine"))
    )).scalars().all())
    provider_ids = [provider.id for provider in providers]
    appointment_rows = list((await session.execute(
        select(Appointment, ProviderSlot, Provider)
        .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id).join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(Appointment.tenant_id == account.tenant_id, ProviderSlot.provider_id.in_(provider_ids or [uuid.uuid4()]))
        .order_by(ProviderSlot.starts_at)
    )).all())
    identity = {"name": f"Dr. {account.first_name} {account.last_name}", "specialty": account.specialty, "initials": f"{account.first_name[:1]}{account.last_name[:1]}"}
    patient_items = [{"id": str(ticket.id), "ticket_number": ticket.ticket_number, "summary": ticket.raw_intake_text, "symptom_description": ticket.raw_intake_text, "matched_condition_name": (ticket.matched_condition_id or "Unclassified").replace("_", " ").title(), "assigned_specialty": ticket.assigned_specialty, "specialty": ticket.assigned_specialty, "urgency_level": ticket.urgency_level, "queue_status": ticket.queue_status, "status": "ASSIGNED" if ticket.assigned_specialist_id == account.id else "UNASSIGNED", "assigned_to_me": ticket.assigned_specialist_id == account.id, "created_at": ticket.created_at.isoformat()} for ticket in tickets]
    appointment_items = [{"id": str(appointment.id), "ticket_id": str(appointment.ticket_id), "title": f"{appointment.customer_phone} · {provider.full_name}", "specialty": provider.specialty, "status": appointment.status, "scheduled_at": slot.starts_at.isoformat(), "subtitle": provider.room_label} for appointment, slot, provider in appointment_rows]
    if resource == "dashboard":
        assigned = [ticket for ticket in tickets if ticket.assigned_specialist_id == account.id]
        return {"identity": identity, "stats": [{"title": "Assigned patients", "value": len(assigned), "tone": "sky"}, {"title": "Being seen", "value": sum(ticket.queue_status == "BEING_SEEN" for ticket in assigned), "tone": "amber"}, {"title": "Appointments", "value": sum(item["status"] == "BOOKED" for item in appointment_items), "tone": "violet"}, {"title": "Critical", "value": sum(ticket.urgency_level == "CRITICAL" for ticket in assigned), "tone": "rose"}], "activity": patient_items[:8]}
    if resource in {"queue", "patients"}:
        return {"identity": identity, "items": patient_items}
    if resource == "appointments":
        return {"identity": identity, "items": appointment_items}
    if resource == "schedule":
        slots = list((await session.execute(select(ProviderSlot, Provider).join(Provider, Provider.id == ProviderSlot.provider_id).where(ProviderSlot.provider_id.in_(provider_ids or [uuid.uuid4()])).order_by(ProviderSlot.starts_at))).all())
        return {"identity": identity, "items": [{"id": str(slot.id), "title": provider.full_name, "scheduled_at": slot.starts_at.isoformat(), "status": "BOOKED" if slot.is_booked else "LOCKED" if slot.is_locked else "AVAILABLE", "subtitle": provider.room_label} for slot, provider in slots]}
    if resource == "notes":
        notes = list((await session.execute(select(ConsultationNote).where(ConsultationNote.tenant_id == account.tenant_id, ConsultationNote.specialist_id == account.id).order_by(ConsultationNote.updated_at.desc()))).scalars().all())
        return {"identity": identity, "items": [{"id": str(note.id), "title": f"Ticket {note.ticket_id}", "body": note.body, "updated_at": note.updated_at.isoformat(), "status": "SIGNED"} for note in notes]}
    if resource == "messages":
        messages = list((await session.execute(select(SpecialistMessage).where(SpecialistMessage.tenant_id == account.tenant_id, SpecialistMessage.specialist_id == account.id).order_by(SpecialistMessage.created_at.desc()))).scalars().all())
        return {"identity": identity, "items": [{"id": str(message.id), "title": message.sender_label, "body": message.body, "created_at": message.created_at.isoformat(), "status": "READ" if message.is_read else "UNREAD"} for message in messages]}
    if resource == "earnings":
        completed = [row for row in appointment_rows if row[0].status == "COMPLETED"]
        fee = 15000
        return {"identity": identity, "stats": [{"title": "Completed consultations", "value": len(completed), "tone": "sky"}, {"title": "Gross earnings", "value": f"₦{len(completed) * fee:,}", "tone": "violet"}], "items": [{**item, "value": f"₦{fee:,}"} for item in appointment_items if item["status"] == "COMPLETED"]}
    if resource == "notifications":
        return {"identity": identity, "notifications": [{**item, "title": f"Patient update · {item['ticket_number']}", "type": "QUEUE_UPDATE", "is_read": False} for item in patient_items[:10]]}
    return {"identity": identity, "items": [{"id": str(account.id), "title": identity["name"], "subtitle": account.specialty or "General Medicine", "status": "ACTIVE"}]}

@router.patch("/specialist/patients/{ticket_id}/assign-self")
async def assign_specialist_patient(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    account = await require_specialist(request, session)
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), ticket_visible_to_tenant(account.tenant_id)).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.assigned_specialist_id not in {None, account.id}:
        raise HTTPException(status_code=409, detail="Ticket is assigned to another specialist")
    ticket.assigned_specialist_id = account.id
    await session.commit()
    return build_ticket_response(ticket)

@router.patch("/specialist/patients/{ticket_id}/status")
async def specialist_patient_status(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    payload = await request.json()
    account = await require_specialist(request, session)
    status = payload.get("queue_status")
    if status not in {"QUEUED", "BEING_SEEN", "RESOLVED"}:
        raise HTTPException(status_code=422, detail="Invalid queue status")
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), ticket_visible_to_tenant(account.tenant_id)).with_for_update())
    if not ticket or ticket.assigned_specialist_id != account.id:
        raise HTTPException(status_code=404, detail="Assigned ticket not found")
    ticket.queue_status = status
    ticket.version += 1
    await session.commit()
    response = build_ticket_response(ticket)
    await broadcast_ticket_event(ticket, "ticket.updated", response.model_dump())
    return response

@router.patch("/specialist/patients/{ticket_id}/escalate")
async def specialist_patient_escalate(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    return await escalate_ticket(ticket_id, request, session)

@router.post("/specialist/patients/{ticket_id}/notes", status_code=201)
async def create_consultation_note(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_specialist(request, session)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 3:
        raise HTTPException(status_code=422, detail="Consultation note is required")
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), ticket_visible_to_tenant(account.tenant_id), Ticket.assigned_specialist_id == account.id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Assigned ticket not found")
    note = ConsultationNote(tenant_id=account.tenant_id, ticket_id=ticket.id, specialist_id=account.id, body=body)
    session.add(note)
    await session.commit()
    return {"id": str(note.id), "ticket_id": str(ticket.id), "body": note.body, "created_at": note.created_at}

@router.post("/specialist/messages", status_code=201)
async def create_specialist_message(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_specialist(request, session)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 2:
        raise HTTPException(status_code=422, detail="Message body is required")
    message = SpecialistMessage(tenant_id=account.tenant_id, specialist_id=account.id, sender_label=str(payload.get("sender_label") or "Specialist"), body=body, is_read=True)
    session.add(message)
    await session.commit()
    return {"id": str(message.id), "body": message.body, "created_at": message.created_at}

@router.post("/admin/maintenance/retention")
async def enforce_retention(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    now = utc_now()
    sessions = await session.execute(delete(AuthSession).where(AuthSession.refresh_expires_at < now - timedelta(days=settings.session_retention_days)))
    audits = await session.execute(delete(AuditLog).where(AuditLog.tenant_id == account.tenant_id, AuditLog.timestamp < now - timedelta(days=settings.audit_retention_days)))
    leads = await session.execute(delete(DemoRequest).where(DemoRequest.tenant_id == account.tenant_id, DemoRequest.created_at < now - timedelta(days=settings.lead_retention_days)))
    await write_audit_log(session, AuditAction.DATA_DELETION_REQUEST, actor_id=str(account.id), actor_type="ADMIN", tenant_id=str(account.tenant_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="RetentionJob", metadata={"policy": "configured_retention"})
    await session.commit()
    return {"sessions_deleted": sessions.rowcount or 0, "audit_logs_deleted": audits.rowcount or 0, "demo_leads_deleted": leads.rowcount or 0}

@router.post("/{entity}/{resource}", status_code=201)
async def create_operational_record(entity: str, resource: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if entity not in {"pharmacy", "lab", "hmo", "moh", "admin"} or resource not in OPERATIONAL_RESOURCES:
        raise HTTPException(status_code=404, detail="Operational resource not found")
    account = await require_roles(request, session, {"admin"})
    payload = await request.json()
    title = str(payload.get("title") or "").strip()
    if len(title) < 2:
        raise HTTPException(status_code=422, detail="Record title is required")
    record = OperationalRecord(tenant_id=account.tenant_id, entity=entity, resource=resource, title=title, description=str(payload.get("description") or "").strip() or None, status=str(payload.get("status") or "ACTIVE").strip().upper())
    session.add(record)
    await session.commit()
    return {"id": str(record.id), "title": record.title, "description": record.description, "status": record.status, "created_at": record.created_at}

@router.patch("/{entity}/{resource}/{record_id}")
async def update_operational_record(entity: str, resource: str, record_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if entity not in {"pharmacy", "lab", "hmo", "moh", "admin"} or resource not in OPERATIONAL_RESOURCES:
        raise HTTPException(status_code=404, detail="Operational resource not found")
    account = await require_roles(request, session, {"admin"})
    record = await session.scalar(select(OperationalRecord).where(OperationalRecord.id == uuid.UUID(record_id), OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == entity, OperationalRecord.resource == resource).with_for_update())
    if not record:
        raise HTTPException(status_code=404, detail="Operational record not found")
    payload = await request.json()
    for field in ("title", "description", "status"):
        if field in payload:
            value = str(payload[field] or "").strip()
            if field == "title" and len(value) < 2:
                raise HTTPException(status_code=422, detail="Record title is required")
            setattr(record, field, value.upper() if field == "status" else value or None)
    record.updated_at = utc_now()
    await session.commit()
    return {"id": str(record.id), "title": record.title, "description": record.description, "status": record.status, "updated_at": record.updated_at}

@router.get("/{entity}/{resource}")
async def operational_portal(entity: str, resource: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    operational_entities = {"nurse", "clinic", "hospital"}
    sector_entities = {"pharmacy", "lab", "hmo", "moh", "admin"}
    if entity not in operational_entities | sector_entities or resource not in OPERATIONAL_RESOURCES:
        raise HTTPException(status_code=404, detail="Operational resource not found")
    allowed_roles = {"admin"} if entity in sector_entities else {"nurse", "doctor", "hospital_admin", "admin"}
    account = await require_roles(request, session, allowed_roles)
    tenant = await session.get(Tenant, account.tenant_id)
    tickets = list((await session.execute(
        select(Ticket).where(ticket_visible_to_tenant(account.tenant_id)).order_by(Ticket.created_at.desc())
    )).scalars().all())
    providers = list((await session.execute(
        select(Provider).where(Provider.tenant_id == account.tenant_id, Provider.is_active.is_(True)).order_by(Provider.full_name)
    )).scalars().all())
    slots = list((await session.execute(
        select(ProviderSlot, Provider).join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(ProviderSlot.tenant_id == account.tenant_id).order_by(ProviderSlot.starts_at)
    )).all())
    appointments = list((await session.execute(
        select(Appointment, ProviderSlot, Provider)
        .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(Appointment.tenant_id == account.tenant_id).order_by(ProviderSlot.starts_at)
    )).all())
    identity = {
        "name": tenant.name if tenant else entity.title(),
        "subtitle": tenant.state_location if tenant else "Operational workspace",
        "badge": account.role.replace("_", " ").title(),
        "initials": "".join(part[0] for part in (tenant.name if tenant else entity).split()[:2]).upper(),
    }
    ticket_items = [
        {"id": str(ticket.id), "ticket_number": ticket.ticket_number, "summary": ticket.raw_intake_text, "urgency_level": ticket.urgency_level, "queue_status": ticket.queue_status, "specialty": ticket.assigned_specialty, "created_at": ticket.created_at.isoformat()}
        for ticket in tickets
    ]
    if entity in sector_entities:
        stored_records = list((await session.execute(select(OperationalRecord).where(OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == entity, OperationalRecord.resource == resource).order_by(OperationalRecord.updated_at.desc()))).scalars().all())
        accounts = list((await session.execute(select(AuthAccount).where(AuthAccount.tenant_id == account.tenant_id).order_by(AuthAccount.created_at.desc()))).scalars().all())
        audit_rows = list((await session.execute(select(AuditLog).where(AuditLog.tenant_id == account.tenant_id).order_by(AuditLog.timestamp.desc()).limit(100))).scalars().all())
        unique_phones = sorted({ticket.customer_phone for ticket in tickets})
        appointment_items = [{"id": str(appointment.id), "title": f"{provider.full_name} · {appointment.customer_phone}", "status": appointment.status, "scheduled_at": slot.starts_at.isoformat(), "specialty": provider.specialty} for appointment, slot, provider in appointments]
        record_items = ticket_items
        if entity == "pharmacy":
            record_items = [{**item, "title": f"Medication review · {item['ticket_number']}", "status": "DISPENSED" if item["queue_status"] == "RESOLVED" else "PENDING"} for item in ticket_items]
        elif entity == "lab":
            record_items = [{**item, "title": f"Diagnostic request · {item['ticket_number']}", "status": "RELEASED" if item["queue_status"] == "RESOLVED" else "PENDING"} for item in ticket_items]
        elif entity == "hmo":
            record_items = appointment_items
        elif entity == "moh":
            condition_counts: dict[str, int] = {}
            for ticket in tickets:
                key = ticket.matched_condition_id or "unclassified"
                condition_counts[key] = condition_counts.get(key, 0) + 1
            record_items = [{"id": key, "title": key.replace("_", " ").title(), "value": count, "status": "ACTIVE"} for key, count in sorted(condition_counts.items())]
        elif entity == "admin":
            if resource == "people":
                record_items = [{"id": str(row.id), "full_name": f"{row.first_name} {row.last_name}", "subtitle": row.role.replace("_", " ").title(), "status": "ACTIVE" if row.is_active else "DISABLED", "created_at": row.created_at.isoformat()} for row in accounts]
            elif resource == "messages":
                record_items = [{"id": str(row.id), "title": row.action, "body": f"{row.actor_type} · {row.resource_type or 'System'}", "created_at": row.timestamp.isoformat(), "status": "RECORDED"} for row in audit_rows]
            elif resource == "vitals":
                return {"identity": identity, "items": [{"id": "api", "title": "API", "status": "HEALTHY"}, {"id": "redis", "title": "Redis", "status": "CONNECTED" if request.app.state.redis.available else "DEGRADED"}, {"id": "neo4j", "title": "Neo4j", "status": "CONNECTED" if request.app.state.knowledge_graph.available else "FALLBACK"}]}
        stored_items = [{"id": str(row.id), "title": row.title, "description": row.description, "status": row.status, "updated_at": row.updated_at.isoformat(), "editable": True} for row in stored_records]
        record_items = stored_items + record_items
        if resource == "dashboard":
            return {"identity": identity, "stats": [{"title": "Patient records", "value": len(unique_phones), "tone": "sky"}, {"title": "Active tickets", "value": sum(ticket.queue_status != "RESOLVED" for ticket in tickets), "tone": "amber"}, {"title": "Appointments", "value": len(appointments), "tone": "violet"}, {"title": "Users", "value": len(accounts), "tone": "slate"}], "activity": record_items[:8]}
        if resource == "settings":
            return {"identity": identity, "items": [{"id": str(tenant.id), "title": tenant.name, "subtitle": tenant.state_location, "status": tenant.status}] if tenant else []}
        if resource == "facilities":
            return {"identity": identity, "items": [{"id": str(tenant.id), "facility_name": tenant.name, "location": tenant.state_location, "status": tenant.status}] if tenant else []}
        if resource in {"members", "patients"}:
            return {"identity": identity, "items": [{"id": phone, "name": f"Member {index + 1}", "subtitle": phone, "status": "ACTIVE"} for index, phone in enumerate(unique_phones)]}
        if resource in {"claims", "payments"}:
            return {"identity": identity, "items": appointment_items}
        if resource in {"analytics", "utilization", "reports", "surveillance"}:
            return {"identity": identity, "chartData": record_items}
        if resource == "notifications":
            return {"identity": identity, "notifications": [{**item, "type": "QUEUE_UPDATE", "is_read": False} for item in record_items[:10]]}
        return {"identity": identity, "items": record_items}
    if resource == "dashboard":
        active = [ticket for ticket in tickets if ticket.queue_status != "RESOLVED"]
        return {
            "identity": identity,
            "stats": [
                {"title": "Active patients", "value": len(active), "tone": "sky"},
                {"title": "Critical", "value": sum(ticket.urgency_level == "CRITICAL" and ticket.queue_status != "RESOLVED" for ticket in tickets), "tone": "rose"},
                {"title": "Appointments", "value": sum(appointment.status == "BOOKED" for appointment, _slot, _provider in appointments), "tone": "amber"},
                {"title": "Providers on roster", "value": len(providers), "tone": "slate"},
            ],
            "activity": ticket_items[:8],
        }
    if resource == "queue":
        return {"identity": identity, "items": [item for item in ticket_items if item["queue_status"] != "RESOLVED"]}
    if resource in {"people", "doctors", "specialists"}:
        return {"identity": identity, "items": [{"id": str(provider.id), "full_name": provider.full_name, "specialty": provider.specialty, "status": "ACTIVE", "subtitle": provider.room_label} for provider in providers]}
    if resource in {"patients", "vitals", "care-plans"}:
        return {"identity": identity, "items": ticket_items}
    if resource in {"appointments", "visits"}:
        return {"identity": identity, "items": [{"id": str(appointment.id), "title": f"{provider.full_name} · {provider.specialty}", "status": appointment.status, "scheduled_at": slot.starts_at.isoformat(), "subtitle": f"{appointment.customer_phone} · {provider.room_label}"} for appointment, slot, provider in appointments]}
    if resource == "schedule":
        return {"identity": identity, "items": [{"id": str(slot.id), "title": provider.full_name, "specialty": provider.specialty, "scheduled_at": slot.starts_at.isoformat(), "status": "BOOKED" if slot.is_booked else "LOCKED" if slot.is_locked else "AVAILABLE", "subtitle": provider.room_label} for slot, provider in slots]}
    if resource == "notifications":
        return {"identity": identity, "notifications": [{**item, "title": f"Queue update · {item['ticket_number']}", "type": "QUEUE_UPDATE", "is_read": False} for item in ticket_items[:10]]}
    if resource == "settings":
        return {"identity": identity, "items": [{"id": str(tenant.id), "title": tenant.name, "subtitle": tenant.state_location, "status": tenant.status}] if tenant else []}
    if resource == "departments":
        names = sorted({ticket.assigned_specialty or "Front Desk" for ticket in tickets} | {provider.specialty for provider in providers})
        return {"identity": identity, "items": [{"id": name, "name": name, "status": "ACTIVE", "summary": f"{sum((ticket.assigned_specialty or 'Front Desk') == name and ticket.queue_status != 'RESOLVED' for ticket in tickets)} active patients"} for name in names]}
    condition_counts: dict[str, int] = {}
    for ticket in tickets:
        label = ticket.matched_condition_id or "unclassified"
        condition_counts[label] = condition_counts.get(label, 0) + 1
    return {"identity": identity, "chartData": [{"id": label, "title": label.replace("_", " ").title(), "value": count, "status": "ACTIVE"} for label, count in sorted(condition_counts.items())]}

def register_routes(app: Any) -> None:
    app.include_router(router)
