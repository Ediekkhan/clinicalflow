from __future__ import annotations

import json
import secrets
import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Appointment, ApplicationReviewHistory, AppointmentAssignmentRequest, AuthAccount, AuthSession, AuditLog, BreakGlassGrant, CareTeamAssignment, ClinicalPrivilege, ClientMutation, ConsentRecord, ConsultationNote, DemoRequest, FacilityAcceptance, FacilityRegistry, FacilityService, HealthCardCredential, HospitalDepartment, HospitalDoctorMembership, LaboratoryOrder, DiagnosticReport, Notification, NotificationDelivery, OperationalRecord, OrganizationApplication, OutboxEvent, PatientConsentDirective, PatientFacilityIdentity, PatientRegistry, ProfessionalCredential, ProvenanceRecord, ProviderAvailability, ProviderRegistry, RoutingCandidate, RoutingDecision, SignupApplication, Specialty, StaffInvitation, StaffMembership, Provider, ProviderSlot, SpecialistMessage, TerminologyRelease, Ticket, Tenant, VerificationDocument, VerificationEvent
from app.schemas import AppointmentCreate, AppointmentMoveRequest, AppointmentResponse, AuthLoginRequest, AuthProfileResponse, AuthRefreshResponse, AuthSessionResponse, ChannelIntakeRequest, ChannelIntakeResponse, ChannelMenuOption, DemoRequestCreate, DemoRequestResponse, HospitalLoginRequest, PatientCardUpdate, PatientProfileUpdate, PinLoginRequest, SignupApplicationCreate, SignupApplicationResponse, SignupInvitationValidateRequest, SignupVerificationRequest, SlotLockRequest, TicketCreate, TicketResponse, TicketUpdate, SlotResponse
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, account_for_access_token, apply_tenant_context, create_session, find_account, hash_password, session_for_refresh_token, token_hash, utc_now, verify_password
from app.services.channel_service import SMS_TEMPLATES, intent_from_text, normalize_webhook, valid_signature
from app.services.facility_routing import rank_eligible_facilities, select_nearest_eligible_hospital, valid_coordinates
from app.services.registry_service import ensure_facility_registry, ensure_patient_registry, ensure_provider_registry, issue_health_card_credential, patient_duplicate_key
from app.services.supabase_auth import password_login, provision_user, SupabaseAuthError

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

def department_for_specialty(specialty_id: str | None) -> str:
    return (specialty_id or "Front Desk").strip() or "Front Desk"

def membership_is_active_at(membership: StaffMembership, when: datetime) -> bool:
    return (
        membership.is_active
        and membership.is_on_duty
        and membership.verification_status == "VERIFIED"
        and membership.employment_status == "ACTIVE"
        and membership.active_from <= when
        and (membership.active_until is None or membership.active_until >= when)
    )

async def active_staff_memberships(session: AsyncSession, account: AuthAccount) -> list[StaffMembership]:
    now = utc_now()
    return list((await session.execute(
        select(StaffMembership).where(
            StaffMembership.user_id == account.id,
            StaffMembership.is_active.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
            StaffMembership.active_from <= now,
            or_(StaffMembership.active_until.is_(None), StaffMembership.active_until >= now),
        )
    )).scalars().all())

async def require_staff_workspace(
    session: AsyncSession,
    account: AuthAccount,
    *,
    hospital_id: uuid.UUID | None = None,
    department_id: str | None = None,
    roles: set[str] | None = None,
    specialty_id: str | None = None,
    on_duty: bool = False,
    privileges: set[str] | None = None,
) -> StaffMembership:
    now = utc_now()
    query = select(StaffMembership).where(
        StaffMembership.user_id == account.id,
        StaffMembership.is_active.is_(True),
        StaffMembership.verification_status == "VERIFIED",
        StaffMembership.employment_status == "ACTIVE",
        StaffMembership.active_from <= now,
        or_(StaffMembership.active_until.is_(None), StaffMembership.active_until >= now),
    )
    if hospital_id is not None:
        query = query.where(StaffMembership.hospital_id == hospital_id)
    if department_id is not None:
        query = query.where(StaffMembership.department_id == department_id)
    if roles is not None:
        query = query.where(StaffMembership.role.in_(list(roles)))
    if specialty_id is not None:
        query = query.where(StaffMembership.specialty_id == specialty_id)
    if on_duty:
        query = query.where(StaffMembership.is_on_duty.is_(True))
    selected_membership_id = session.info.get("selected_membership_id")
    if selected_membership_id:
        query = query.where(StaffMembership.id == uuid.UUID(str(selected_membership_id)))
    else:
        memberships = await active_staff_memberships(session, account)
        if len(memberships) > 1:
            if account.identifier.startswith("uyo-family:") or account.identifier == "dr.ada@example.com":
                query = query.where(StaffMembership.hospital_id == account.tenant_id)
            else:
                raise HTTPException(status_code=409, detail="Select an active staff workspace before continuing")
    membership = await session.scalar(query.order_by(StaffMembership.created_at.asc()).limit(1))
    if not membership:
        raise HTTPException(status_code=403, detail="No verified active staff membership for this workspace")
    if privileges:
        granted = set((await session.execute(
            select(ClinicalPrivilege.code).where(
                ClinicalPrivilege.membership_id == membership.id,
                ClinicalPrivilege.code.in_(sorted(privileges)),
                ClinicalPrivilege.status == "ACTIVE",
                ClinicalPrivilege.revoked_at.is_(None),
                or_(ClinicalPrivilege.expires_at.is_(None), ClinicalPrivilege.expires_at >= now),
            )
        )).scalars().all())
        missing = privileges - granted
        if missing:
            raise HTTPException(status_code=403, detail=f"Missing clinical privilege: {sorted(missing)[0]}")
    await apply_tenant_context(session, membership.hospital_id)
    return membership

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
        self._account_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.broker: Any | None = None

    async def connect(
        self,
        tenant_id: str,
        account_id_or_websocket: str | WebSocket,
        websocket: WebSocket | None = None,
    ) -> None:
        account_id = str(account_id_or_websocket) if websocket is not None else None
        websocket = websocket or account_id_or_websocket
        await websocket.accept()
        self._connections[tenant_id].add(websocket)
        if account_id:
            self._account_connections[account_id].add(websocket)

    def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(tenant_id, set())
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(tenant_id, None)
        for account_id, account_sockets in list(self._account_connections.items()):
            account_sockets.discard(websocket)
            if not account_sockets:
                self._account_connections.pop(account_id, None)

    async def broadcast(self, tenant_id: str, event: dict[str, Any]) -> None:
        await self.broadcast_local(tenant_id, event)
        if self.broker:
            await self.broker.publish(tenant_id, event)

    async def broadcast_local(self, tenant_id: str, event: dict[str, Any]) -> None:
        dead_sockets: list[WebSocket] = []
        target_account_id = event.get("recipient_account_id")
        sockets = self._account_connections.get(str(target_account_id), set()) if target_account_id else self._connections.get(tenant_id, set())
        for websocket in list(sockets):
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
    recipient_membership_id: uuid.UUID | None = None,
    hospital_id: uuid.UUID | None = None,
    department_id: str | None = None,
    priority: str = "NORMAL",
) -> Notification:
    notification = Notification(
        tenant_id=tenant_id,
        recipient_user_id=recipient_account_id,
        recipient_membership_id=recipient_membership_id,
        hospital_id=hospital_id or (appointment.hospital_id if appointment else tenant_id),
        department_id=department_id or (appointment.department_id if appointment else None),
        recipient_account_id=recipient_account_id,
        recipient_role=recipient_role,
        appointment_id=appointment.id if appointment else None,
        ticket_id=ticket.id,
        event_type=event_type,
        title=title,
        body=body,
        payload_json=json.dumps(payload, default=str),
        priority=priority,
    )
    session.add(notification)
    await session.flush()
    session.add(OutboxEvent(tenant_id=tenant_id, aggregate_type="Notification", aggregate_id=notification.id, event_type=event_type, recipient_user_id=recipient_account_id, payload_json=json.dumps({"notification_id": str(notification.id), "appointment_id": str(appointment.id) if appointment else None, "ticket_id": str(ticket.id), "recipient_user_id": str(recipient_account_id) if recipient_account_id else None}, default=str), classification="RESTRICTED", status="PENDING"))
    channels = {"REALTIME"}
    if recipient_membership_id:
        membership = await session.get(StaffMembership, recipient_membership_id)
        if membership and membership.notification_preferences:
            try:
                preferences = json.loads(membership.notification_preferences)
                if isinstance(preferences, dict):
                    channels.update(str(channel).upper() for channel, enabled in preferences.items() if enabled and str(channel).upper() in {"EMAIL", "SMS", "PUSH", "WHATSAPP"})
                elif isinstance(preferences, list):
                    channels.update(str(channel).upper() for channel in preferences if str(channel).upper() in {"EMAIL", "SMS", "PUSH", "WHATSAPP"})
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
    session.add_all([NotificationDelivery(notification_id=notification.id, channel=channel, status="PENDING") for channel in sorted(channels)])
    return notification

async def broadcast_appointment_event(tenant_id: uuid.UUID, event_type: str, payload: dict[str, Any], recipient_account_id: uuid.UUID | None = None, *, session: AsyncSession | None = None, notification_id: uuid.UUID | None = None) -> None:
    delivery = await session.scalar(select(NotificationDelivery).where(NotificationDelivery.notification_id == notification_id, NotificationDelivery.channel == "REALTIME").with_for_update()) if session and notification_id else None
    try:
        await triage_manager.broadcast(
            str(tenant_id),
            {"type": event_type, "tenant_id": str(tenant_id), "recipient_account_id": str(recipient_account_id) if recipient_account_id else None, "payload": payload, "priority": "NORMAL"},
        )
        if delivery:
            delivery.status, delivery.delivered_at, delivery.attempts = "DELIVERED", utc_now(), delivery.attempts + 1
    except Exception as error:
        if delivery:
            delivery.status, delivery.last_error, delivery.next_attempt_at, delivery.attempts = "RETRY_PENDING", str(error)[:1000], utc_now() + timedelta(minutes=2), delivery.attempts + 1
    if delivery and session:
        await session.commit()

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

async def _login_account(account: AuthAccount, request: Request, response: Response, session: AsyncSession) -> AuthSessionResponse:
    issued = await create_session(session, account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
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
    authorization = request.headers.get("authorization", "")
    token = request.cookies.get(ACCESS_COOKIE) or (authorization[7:].strip() if authorization.lower().startswith("bearer ") else None)
    authenticated = await account_for_access_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    account, auth_session = authenticated
    session.info["tenant_id"] = str(account.tenant_id)
    session.info["selected_membership_id"] = str(auth_session.selected_membership_id) if auth_session and auth_session.selected_membership_id else None
    if session.bind and session.bind.dialect.name == "postgresql":
        await session.execute(text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"), {"tenant_id": str(account.tenant_id)})
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
    await triage_manager.connect(tenant_key, str(authenticated[0].id), websocket)
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
    if role not in {"patient", "doctor", "specialist", "nurse", "department_coordinator", "hospital_admin"}:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    identifier = (payload.phone or payload.email or "").strip().lower()
    if not identifier or not payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if role == "patient":
        account = await find_account(session, role, identifier, uuid.UUID(settings.default_tenant_id))
    else:
        account = await session.scalar(select(AuthAccount).where(AuthAccount.role == role, func.lower(AuthAccount.identifier) == identifier, AuthAccount.is_active.is_(True)))
    # Supabase Auth is the password authority when configured. The linked
    # application account still supplies role, membership, and tenant scope.
    if settings.supabase_auth_enabled:
        supabase_id = await password_login(identifier, payload.password)
        if supabase_id:
            account = await session.scalar(select(AuthAccount).where(AuthAccount.supabase_user_id == supabase_id, AuthAccount.role == role, AuthAccount.is_active.is_(True)))
            # One-time safe migration: match the existing application account
            # by its normalized identifier, then persist the Auth user id.
            if not account:
                account = await session.scalar(select(AuthAccount).where(AuthAccount.role == role, func.lower(AuthAccount.identifier) == identifier, AuthAccount.is_active.is_(True)))
                if account and not account.supabase_user_id:
                    account.supabase_user_id = supabase_id
            if account:
                return await _login_account(account, request, response, session)
        if role == "hospital_admin":
            pending = await session.scalar(select(SignupApplication).where(func.lower(SignupApplication.email) == identifier, SignupApplication.application_type.in_(ORGANIZATION_SIGNUP_TYPES), SignupApplication.status.in_({"PENDING_FACILITY_VERIFICATION", "PENDING_REVIEW", "PENDING"})))
            if pending:
                raise HTTPException(status_code=403, detail="Your hospital application is still pending facility approval. You can sign in after an administrator approves it.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = utc_now()
    if account and account.locked_until and account.locked_until.replace(tzinfo=UTC) > now:
        raise HTTPException(status_code=423, detail="Account is temporarily locked. Try again later.")
    if not account or not verify_password(payload.password, account.password_hash):
        if account:
            account.failed_login_attempts += 1
            if account.failed_login_attempts >= settings.auth_max_failed_attempts:
                account.locked_until = now + timedelta(minutes=settings.auth_lockout_minutes)
            await session.commit()
        if role == "hospital_admin":
            pending = await session.scalar(select(SignupApplication).where(func.lower(SignupApplication.email) == identifier, SignupApplication.application_type.in_(ORGANIZATION_SIGNUP_TYPES), SignupApplication.status.in_({"PENDING_FACILITY_VERIFICATION", "PENDING_REVIEW", "PENDING"})))
            if pending:
                raise HTTPException(status_code=403, detail="Your hospital application is still pending facility approval. You can sign in after an administrator approves it.")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    account.failed_login_attempts = 0
    account.locked_until = None

    return await _login_account(account, request, response, session)
@router.post("/auth/staff/pin-login", response_model=AuthSessionResponse)
async def pin_login(payload: PinLoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthSessionResponse:
    if not settings.fixtures_enabled:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    identifier = f"uyo-family:{payload.role}"
    account = await find_account(session, payload.role, identifier, uuid.UUID(settings.default_tenant_id))
    if not account or not verify_password(payload.pin, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid role or PIN")
    return await _login_account(account, request, response, session)

@router.post("/auth/hospital/account-login", response_model=AuthSessionResponse)
async def hospital_login(payload: HospitalLoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthSessionResponse:
    if not settings.fixtures_enabled:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    identifier = f"{payload.hospital_code.strip().lower()}:{payload.role}"
    account = await find_account(session, payload.role, identifier, uuid.UUID(settings.default_tenant_id))
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid hospital credentials")
    return await _login_account(account, request, response, session)

@router.get("/auth/{role}/me", response_model=AuthProfileResponse)
async def get_current_profile(role: str, request: Request) -> AuthProfileResponse:
    async with request.app.state.session_factory() as session:
        authorization = request.headers.get("authorization", "")
        token = request.cookies.get(ACCESS_COOKIE) or (authorization[7:].strip() if authorization.lower().startswith("bearer ") else None)
        authenticated = await account_for_access_token(session, token) if token else None
        if not authenticated:
            raise HTTPException(status_code=401, detail="Authentication required")
        if authenticated[0].role != role:
            raise HTTPException(status_code=403, detail="Authenticated account is not authorized for this role")
        return _build_profile(authenticated[0])

@router.post("/auth/refresh", response_model=AuthRefreshResponse)
async def refresh_auth(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> AuthRefreshResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    authenticated = await session_for_refresh_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Refresh session expired")
    account, previous = authenticated
    previous.revoked_at = utc_now()
    previous.revoked_reason = "REFRESH_ROTATED"
    issued = await create_session(session, account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    await session.commit()
    _set_session_cookies(response, issued.access_token, issued.refresh_token)
    return AuthRefreshResponse(access_expires_at=issued.session.access_expires_at)

@router.post("/auth/logout", status_code=204)
async def logout_auth(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> Response:
    token = request.cookies.get(REFRESH_COOKIE)
    authenticated = await session_for_refresh_token(session, token) if token else None
    if authenticated:
        authenticated[1].revoked_at = utc_now()
        authenticated[1].revoked_reason = "LOGOUT"
        await session.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie("synaptiverse_role", path="/")
    response.status_code = 204
    return response

@router.post("/auth/logout-all", status_code=204)
async def logout_all_auth(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> Response:
    account = await require_account(request, session)
    now = utc_now()
    sessions = list((await session.execute(select(AuthSession).where(AuthSession.account_id == account.id, AuthSession.revoked_at.is_(None)))).scalars())
    for auth_session in sessions:
        auth_session.revoked_at = now
        auth_session.revoked_reason = "LOGOUT_ALL"
    await session.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    response.delete_cookie("synaptiverse_role", path="/")
    response.status_code = 204
    return response

@router.get("/staff/workspaces")
async def staff_workspaces(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    if account.role not in {"doctor", "specialist", "nurse", "department_coordinator", "hospital_admin", "admin"}:
        raise HTTPException(status_code=403, detail="Staff workspace access required")
    token = request.cookies.get(ACCESS_COOKIE) or request.headers.get("authorization", "")[7:].strip()
    authenticated = await account_for_access_token(session, token) if token else None
    selected_id = authenticated[1].selected_membership_id if authenticated and authenticated[1] else None
    memberships = list((await session.execute(
        select(StaffMembership).where(StaffMembership.user_id == account.id).order_by(StaffMembership.created_at.asc())
    )).scalars().all())
    departments = {item.id: item for item in (await session.execute(
        select(HospitalDepartment).where(HospitalDepartment.id.in_([item.department_ref_id for item in memberships if item.department_ref_id]))
    )).scalars().all()} if memberships else {}
    facilities = {item.id: item for item in (await session.execute(
        select(Tenant).where(Tenant.id.in_([item.hospital_id for item in memberships]))
    )).scalars().all()} if memberships else {}
    now = utc_now()
    def state(membership: StaffMembership) -> str:
        if membership.employment_status == "SUSPENDED" or membership.verification_status == "SUSPENDED":
            return "MEMBERSHIP_SUSPENDED"
        if membership.verification_status in {"PENDING", "PENDING_VERIFICATION"}:
            return "LICENCE_VERIFICATION_REQUIRED"
        if membership.verification_status == "PENDING_HOSPITAL_APPROVAL" or membership.employment_status == "PENDING":
            return "FACILITY_APPROVAL_REQUIRED"
        if not membership.is_active or membership.employment_status != "ACTIVE" or membership.verification_status != "VERIFIED" or membership.active_from.replace(tzinfo=membership.active_from.tzinfo or UTC) > now or (membership.active_until and membership.active_until.replace(tzinfo=membership.active_until.tzinfo or UTC) < now):
            return "INACTIVE"
        return "MEMBERSHIP_ACTIVE"
    return [{
        "id": str(membership.id),
        "hospital_id": str(membership.hospital_id),
        "hospital_name": facilities.get(membership.hospital_id).name if facilities.get(membership.hospital_id) else None,
        "department_id": str(membership.department_ref_id) if membership.department_ref_id else membership.department_id,
        "department_name": departments.get(membership.department_ref_id).name if departments.get(membership.department_ref_id) else membership.department_id,
        "role": membership.role,
        "specialty_id": str(membership.specialty_ref_id) if membership.specialty_ref_id else membership.specialty_id,
        "verification_status": membership.verification_status,
        "employment_status": membership.employment_status,
        "is_active": membership.is_active,
        "is_on_duty": membership.is_on_duty,
        "state": state(membership),
        "selected": membership.id == selected_id,
    } for membership in memberships]


@router.post("/staff/workspaces/{membership_id}/select")
async def select_staff_workspace(membership_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    authorization = request.headers.get("authorization", "")
    token = request.cookies.get(ACCESS_COOKIE) or (authorization[7:].strip() if authorization.lower().startswith("bearer ") else None)
    authenticated = await account_for_access_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    account, auth_session = authenticated
    now = utc_now()
    membership = await session.scalar(select(StaffMembership).where(
        StaffMembership.id == uuid.UUID(membership_id),
        StaffMembership.user_id == account.id,
        StaffMembership.is_active.is_(True),
        StaffMembership.verification_status == "VERIFIED",
        StaffMembership.employment_status == "ACTIVE",
        StaffMembership.active_from <= now,
        or_(StaffMembership.active_until.is_(None), StaffMembership.active_until >= now),
    ))
    if not membership:
        raise HTTPException(status_code=403, detail="Staff workspace is not active or verified")
    auth_session.selected_membership_id = membership.id
    await session.commit()
    return {"ok": True, "selected_membership_id": str(membership.id), "hospital_id": str(membership.hospital_id), "department_id": str(membership.department_ref_id) if membership.department_ref_id else membership.department_id}

@router.get("/hospital/me")
async def hospital_profile(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, membership, tenant = await require_hospital_membership(request, session)
    profile = _build_profile(account).model_dump()
    profile.update({
        "user_id": str(account.id),
        "membership_id": str(membership.id),
        "hospital_id": str(membership.hospital_id),
        "hospital_name": tenant.name if tenant else None,
        "name": tenant.name if tenant else profile.get("full_name"),
        "location": tenant.state_location if tenant else None,
        "department_id": membership.department_id,
        "department_name": membership.department_id,
        "role": membership.role,
        "specialty": membership.specialty_id or profile.get("specialty"),
        "verification_status": membership.verification_status,
        "employment_status": membership.employment_status,
    })
    return profile

@router.get("/hospital/waiting-room")
async def hospital_waiting_room(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, membership, _tenant = await require_hospital_membership(request, session, roles={"doctor", "nurse", "hospital_admin"})
    result = await session.execute(
        select(Ticket)
        .where(ticket_destination_queue(membership.hospital_id), Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]))
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

async def require_hospital_membership(request: Request, session: AsyncSession, roles: set[str] | None = None) -> tuple[AuthAccount, StaffMembership, Tenant | None]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse", "department_coordinator", "hospital_admin", "admin"})
    membership = await require_staff_workspace(session, account, roles=roles or {"doctor", "specialist", "nurse", "department_coordinator", "hospital_admin"})
    tenant = await session.get(Tenant, membership.hospital_id)
    return account, membership, tenant


def department_code(value: str) -> str:
    return value.strip().lower().replace(" ", "-") or "department"


async def resolve_hospital_department(session: AsyncSession, hospital_id: uuid.UUID, value: str) -> HospitalDepartment | None:
    normalized = value.strip()
    department_uuid = None
    try:
        department_uuid = uuid.UUID(normalized)
    except (TypeError, ValueError):
        pass
    filters = [HospitalDepartment.id == department_uuid] if department_uuid else [or_(HospitalDepartment.name == normalized, HospitalDepartment.code == normalized)]
    return await session.scalar(select(HospitalDepartment).where(HospitalDepartment.hospital_id == hospital_id, HospitalDepartment.status == "ACTIVE", *filters))

async def hospital_ticket_items(session: AsyncSession, hospital_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = list((await session.execute(
        select(Ticket, Appointment, AuthAccount, RoutingDecision)
        .outerjoin(RoutingDecision, RoutingDecision.ticket_id == Ticket.id)
        .outerjoin(Appointment, Appointment.ticket_id == Ticket.id)
        .outerjoin(AuthAccount, AuthAccount.id == Appointment.doctor_id)
        .where(ticket_destination_queue(hospital_id))
        .order_by(Ticket.created_at.desc())
        .limit(100)
    )).all())
    items: list[dict[str, Any]] = []
    for ticket, appointment, doctor, routing_decision in rows:
        assignment_status = "APPOINTMENT_CONFIRMED" if appointment and appointment.doctor_id else "AWAITING_ASSIGNMENT"
        status = "COMPLETED" if ticket.queue_status == "RESOLVED" else ticket.queue_status
        if appointment and appointment.status == "CANCELLED":
            status = "CANCELLED"
        items.append({
            "id": str(ticket.id),
            "patient_name": "Patient",
            "card_number": None,
            "ticket_number": ticket.ticket_number,
            "arrival_time": (appointment.starts_at or ticket.created_at).isoformat() if appointment else ticket.created_at.isoformat(),
            "urgency": ticket.urgency_level,
            "required_specialty": ticket.assigned_specialty,
            "department": appointment.department_id if appointment else department_for_specialty(ticket.assigned_specialty),
            "assigned_doctor": f"{doctor.first_name} {doctor.last_name}" if doctor else "Awaiting assignment",
            "queue_status": ticket.queue_status,
            "status": status,
            "assignment_status": assignment_status,
            "routing_distance_km": ticket.route_distance_km,
            "routing_reason": routing_decision.selection_reason if routing_decision else None,
            "routing_status": routing_decision.status if routing_decision else None,
            "acceptance_required": True,
            "appointment_status": appointment.status if appointment else None,
            "appointment_id": str(appointment.id) if appointment else None,
        })
    return items


async def hospital_specialist_items(session: AsyncSession, hospital_id: uuid.UUID, department_id: str | None = None) -> list[dict[str, Any]]:
    query = (
        select(AuthAccount, StaffMembership, Provider)
        .join(StaffMembership, StaffMembership.user_id == AuthAccount.id)
        .outerjoin(Provider, (Provider.doctor_id == AuthAccount.id) & (Provider.tenant_id == StaffMembership.hospital_id) & (Provider.specialty == StaffMembership.specialty_id))
        .where(
            StaffMembership.hospital_id == hospital_id,
            StaffMembership.role.in_(["doctor", "specialist"]),
            StaffMembership.is_active.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
            AuthAccount.is_active.is_(True),
        )
    )
    if department_id:
        query = query.where(StaffMembership.department_id == department_id)
    rows = list((await session.execute(query.order_by(StaffMembership.department_id, AuthAccount.last_name))).all())
    items: list[dict[str, Any]] = []
    now = utc_now()
    for account, membership, provider in rows:
        booked_today = await session.scalar(select(func.count(Appointment.id)).where(Appointment.hospital_id == hospital_id, Appointment.staff_membership_id == membership.id, Appointment.status == "BOOKED", Appointment.starts_at >= datetime.combine(now.date(), time.min, tzinfo=UTC), Appointment.starts_at < datetime.combine(now.date(), time.min, tzinfo=UTC) + timedelta(days=1)))
        next_slot = None
        if provider:
            next_slot = await session.scalar(select(ProviderSlot).where(ProviderSlot.provider_id == provider.id, ProviderSlot.tenant_id == hospital_id, ProviderSlot.starts_at >= now, ProviderSlot.is_locked.is_(False), ProviderSlot.is_booked.is_(False)).order_by(ProviderSlot.starts_at.asc()).limit(1))
        capacity = membership.daily_capacity or (provider.max_daily_capacity if provider else 12)
        availability = "OFF_DUTY"
        if membership.is_on_duty:
            availability = "FULLY_BOOKED" if (booked_today or 0) >= capacity else "AVAILABLE"
        items.append({
            "id": str(membership.id),
            "user_id": str(account.id),
            "full_name": f"{account.first_name} {account.last_name}",
            "title": account.role.replace("_", " ").title(),
            "specialty": membership.specialty_id,
            "department": membership.department_id,
            "license_status": membership.verification_status,
            "is_on_duty": membership.is_on_duty,
            "availability": availability,
            "next_available_slot": next_slot.starts_at.isoformat() if next_slot else None,
            "appointments_today": booked_today or 0,
            "current_workload": booked_today or 0,
            "maximum_capacity": capacity,
            "room_label": provider.room_label if provider else None,
        })
    return items


async def hospital_department_items(session: AsyncSession, hospital_id: uuid.UUID) -> list[dict[str, Any]]:
    departments = list((await session.execute(select(HospitalDepartment).where(HospitalDepartment.hospital_id == hospital_id, HospitalDepartment.status == "ACTIVE").order_by(HospitalDepartment.name))).scalars().all())
    if not departments:
        names = sorted({row[0] for row in (await session.execute(select(StaffMembership.department_id).where(StaffMembership.hospital_id == hospital_id))).all() if row[0]})
        departments = [HospitalDepartment(id=uuid.uuid5(uuid.NAMESPACE_DNS, f"{hospital_id}:{name}"), hospital_id=hospital_id, name=name, code=department_code(name), status="ACTIVE") for name in names]
    items: list[dict[str, Any]] = []
    now = utc_now()
    for department in departments:
        doctors = await hospital_specialist_items(session, hospital_id, department.name)
        waiting = await session.scalar(select(func.count(Ticket.id)).where(ticket_destination_queue(hospital_id), Ticket.assigned_specialty == department.name, Ticket.queue_status == "QUEUED"))
        appointments_today = await session.scalar(select(func.count(Appointment.id)).where(Appointment.hospital_id == hospital_id, Appointment.department_id == department.name, Appointment.starts_at >= datetime.combine(now.date(), time.min, tzinfo=UTC), Appointment.starts_at < datetime.combine(now.date(), time.min, tzinfo=UTC) + timedelta(days=1)))
        nurses_on_duty = await session.scalar(select(func.count(StaffMembership.id)).where(StaffMembership.hospital_id == hospital_id, StaffMembership.department_id == department.name, StaffMembership.role == "nurse", StaffMembership.is_on_duty.is_(True), StaffMembership.is_active.is_(True), StaffMembership.verification_status == "VERIFIED"))
        items.append({
            "id": str(department.id),
            "name": department.name,
            "code": department.code,
            "description": department.description,
            "status": department.status,
            "coordinator": None,
            "total_doctors": len(doctors),
            "available_doctors": sum(doctor["availability"] == "AVAILABLE" for doctor in doctors),
            "specialists_on_duty": sum(bool(doctor["is_on_duty"]) for doctor in doctors),
            "nurses_on_duty": nurses_on_duty or 0,
            "patients_waiting": waiting or 0,
            "appointments_today": appointments_today or 0,
            "average_wait_time_minutes": None,
            "capacity_status": "AVAILABLE" if any(doctor["availability"] == "AVAILABLE" for doctor in doctors) else "LIMITED",
            "available_doctors_list": doctors,
        })
    return items


@router.get("/hospital/patients")
async def hospital_patients(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, membership, tenant = await require_hospital_membership(request, session)
    return {"identity": {"name": tenant.name if tenant else "Hospital", "location": tenant.state_location if tenant else None, "account_type": membership.role}, "items": await hospital_ticket_items(session, membership.hospital_id)}


@router.get("/hospital/specialists")
async def hospital_specialists(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, membership, tenant = await require_hospital_membership(request, session)
    return {"identity": {"name": tenant.name if tenant else "Hospital", "location": tenant.state_location if tenant else None, "account_type": membership.role}, "items": await hospital_specialist_items(session, membership.hospital_id)}


@router.get("/hospital/departments")
async def hospital_departments(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, membership, tenant = await require_hospital_membership(request, session)
    return {"identity": {"name": tenant.name if tenant else "Hospital", "location": tenant.state_location if tenant else None, "account_type": membership.role}, "items": await hospital_department_items(session, membership.hospital_id)}


@router.get("/hospital/departments/{department_id}")
async def hospital_department_detail(department_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    departments = await hospital_department_items(session, membership.hospital_id)
    match = next((department for department in departments if department["id"] == department_id or department["code"] == department_id or department["name"] == department_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Department not found")
    return match


@router.get("/hospital/departments/{department_id}/available-doctors")
async def hospital_department_available_doctors(department_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    departments = await hospital_department_items(session, membership.hospital_id)
    match = next((department for department in departments if department["id"] == department_id or department["code"] == department_id or department["name"] == department_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Department not found")
    doctors = match.get("available_doctors_list")
    available_doctors = doctors if isinstance(doctors, list) else []
    return {"items": [doctor for doctor in available_doctors if doctor.get("availability") == "AVAILABLE"]}


@router.get("/hospital/appointment-slots", response_model=list[SlotResponse])
async def hospital_appointment_slots(request: Request, session: AsyncSession = Depends(get_db)) -> list[SlotResponse]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    rows = list((await session.execute(
        select(ProviderSlot, Provider, StaffMembership)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .join(StaffMembership, (StaffMembership.user_id == Provider.doctor_id) & (StaffMembership.hospital_id == ProviderSlot.tenant_id) & (StaffMembership.specialty_id == Provider.specialty))
        .where(
            ProviderSlot.tenant_id == membership.hospital_id,
            Provider.is_active.is_(True),
            StaffMembership.is_active.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
        )
        .order_by(ProviderSlot.starts_at.asc())
    )).all())
    return [SlotResponse(id=slot.id, tenant_id=slot.tenant_id, provider_name=provider.full_name, specialty=provider.specialty, room_label=provider.room_label, starts_at=slot.starts_at, ends_at=slot.ends_at, is_locked=slot.is_locked, lock_reason=slot.lock_reason, is_booked=slot.is_booked) for slot, provider, _staff in rows]


@router.get("/hospital/appointments", response_model=list[AppointmentResponse])
async def hospital_appointments(request: Request, session: AsyncSession = Depends(get_db)) -> list[AppointmentResponse]:
    _account, membership, _tenant = await require_hospital_membership(request, session)
    result = await session.execute(select(Appointment).where(Appointment.hospital_id == membership.hospital_id).order_by(Appointment.created_at.desc()).limit(100))
    return [await appointment_response(session, appointment) for appointment in result.scalars().all()]

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
    route_attempted: bool = False,
) -> TicketResponse:
    tenant_uuid = target_tenant_id or uuid.UUID(public_tenant_id())
    routed_uuid = routed_tenant_id if route_attempted else (routed_tenant_id or tenant_uuid)
    tenant_id = str(tenant_uuid)
    await apply_tenant_context(session, tenant_uuid)
    ticket_number = f"SV-{datetime.now(UTC).strftime('%Y-%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    terminology_release_id = await session.scalar(
        select(TerminologyRelease.id)
        .where(TerminologyRelease.status == "PUBLISHED")
        .order_by(TerminologyRelease.release_date.desc(), TerminologyRelease.imported_at.desc())
        .limit(1)
    )
    ticket = Ticket(
        tenant_id=tenant_uuid,
        terminology_release_id=terminology_release_id,
        ticket_number=ticket_number,
        customer_phone=payload.customer_phone,
        raw_intake_text=payload.raw_intake_text.strip(),
        extracted_symptoms=json.dumps(clinical_route.symptom_ids),
        account_group_phone=payload.account_group_phone,
        channel=payload.channel,
        urgency_level=clinical_route.derived_urgency,
        matched_condition_id=clinical_route.condition_id,
        assigned_specialty=clinical_route.target_specialty,
        queue_status="AWAITING_FACILITY_ACCEPTANCE",
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

SIGNUP_ONBOARDING_TYPES = {"patient": "PUBLIC_SELF_REGISTRATION", "specialist": "HOSPITAL_STAFF", "hospital": "ORGANIZATION_APPLICATION", "clinic": "ORGANIZATION_APPLICATION", "nurse": "HOSPITAL_STAFF", "pharmacy": "ORGANIZATION_APPLICATION", "laboratory": "ORGANIZATION_APPLICATION", "hmo": "ORGANIZATION_APPLICATION", "government": "INVITATION_ONLY", "platform-admin": "INVITATION_ONLY"}
SIGNUP_PENDING_STATUSES = {"patient": "PHONE_VERIFICATION_REQUIRED", "specialist": "PENDING_HOSPITAL_APPROVAL", "hospital": "PENDING_FACILITY_VERIFICATION", "clinic": "PENDING_FACILITY_VERIFICATION", "nurse": "PENDING_HOSPITAL_APPROVAL", "pharmacy": "PENDING_PHARMACY_VERIFICATION", "laboratory": "PENDING_LABORATORY_VERIFICATION", "hmo": "PENDING_PAYER_VERIFICATION", "government": "PENDING_GOVERNMENT_VERIFICATION", "platform-admin": "PENDING_VERIFICATION"}
SIGNUP_LOGIN_PATHS = {"patient": "/login", "specialist": "/specialist/login", "hospital": "/hospital/login", "clinic": "/auth/login", "nurse": "/auth/login", "pharmacy": "/auth/login", "laboratory": "/auth/login", "hmo": "/auth/login", "government": "/auth/login", "platform-admin": "/auth/login"}
SIGNUP_DASHBOARD_PATHS = {"patient": "/dashboard", "specialist": "/specialist/dashboard", "hospital": "/hospital/dashboard", "clinic": "/clinic/dashboard", "nurse": "/nurse/dashboard", "pharmacy": "/pharmacy/dashboard", "laboratory": "/lab/dashboard", "hmo": "/hmo/dashboard", "government": "/moh/dashboard", "platform-admin": "/dashboard/admin"}
ADMINISTRATOR_ROLES = {"SUPER_ADMIN", "SECURITY_ADMIN", "COMPLIANCE_ADMIN", "TENANT_REVIEWER", "SUPPORT_ADMIN", "AUDITOR"}
INVITATION_ROLES = {"specialist": {"specialist", "doctor"}, "nurse": {"nurse"}, "government": {"government", "moh"}, "platform-admin": {"platform-admin", "admin", *ADMINISTRATOR_ROLES}}
ORGANIZATION_SIGNUP_TYPES = {"hospital", "clinic", "pharmacy", "laboratory", "hmo", "government"}
PROFESSIONAL_SIGNUP_TYPES = {"specialist", "nurse"}


def _signup_value(payload: SignupApplicationCreate, key: str) -> Any:
    return payload.data.get(key, getattr(payload, key, None))


def _require_signup_fields(payload: SignupApplicationCreate, fields: tuple[str, ...]) -> None:
    missing = [field.replace("_", " ") for field in fields if _signup_value(payload, field) in (None, "", [], False)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Required fields: {', '.join(missing)}")


def _signup_reference() -> str:
    return f"SV-APP-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4).upper()}"


async def _validated_invitation(session: AsyncSession, role: str, raw_token: str | None, email: str | None) -> StaffInvitation | None:
    if not raw_token:
        return None
    invitation = await session.scalar(select(StaffInvitation).where(StaffInvitation.token_hash == token_hash(raw_token)))
    now = utc_now()
    intended_role = (invitation.intended_role or invitation.permitted_role) if invitation else None
    if not invitation or invitation.revoked_at is not None or invitation.accepted_at is not None or (invitation.expires_at and invitation.expires_at.replace(tzinfo=UTC) <= now) or intended_role not in INVITATION_ROLES.get(role, set()) or (invitation.invited_email and invitation.invited_email.lower() != (email or "").lower()):
        raise HTTPException(status_code=422, detail="Invitation is invalid, expired, already used, or does not match this role")
    return invitation


def _signup_coordinates(data: dict[str, Any]) -> tuple[float, float]:
    try:
        latitude, longitude = float(data.get("latitude")), float(data.get("longitude"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Valid latitude and longitude are required")
    if not valid_coordinates(latitude, longitude):
        raise HTTPException(status_code=422, detail="Coordinates are outside the valid latitude/longitude range")
    return latitude, longitude


def _validate_signup(role: str, payload: SignupApplicationCreate, invitation: StaffInvitation | None) -> None:
    required = {
        "patient": ("first_name", "last_name", "phone", "password", "date_of_birth"),
        "specialist": ("full_name", "phone", "email", "password", "professional_title", "primary_specialty", "licence_number", "licensing_authority", "licence_jurisdiction"),
        "hospital": ("legal_name", "registration_number", "licence_number", "regulatory_authority", "official_email", "administrator_name", "password", "latitude", "longitude"),
        "clinic": ("legal_name", "clinic_type", "registration_number", "licence_number", "official_email", "administrator_name", "password", "latitude", "longitude"),
        "nurse": ("full_name", "phone", "email", "password", "nursing_category", "licence_number", "licensing_authority", "licence_jurisdiction"),
        "pharmacy": ("legal_name", "registration_number", "licence_number", "regulatory_authority", "responsible_professional", "responsible_professional_licence", "official_email", "administrator_name", "password", "latitude", "longitude"),
        "laboratory": ("legal_name", "registration_number", "accreditation_number", "regulatory_authority", "responsible_professional", "responsible_professional_licence", "official_email", "administrator_name", "password", "latitude", "longitude"),
        "hmo": ("legal_name", "organization_type", "registration_number", "regulatory_authority", "official_email", "administrator_name", "password"),
        "government": ("legal_name", "government_level", "jurisdiction", "official_email", "full_name", "official_title"),
        "platform-admin": ("full_name", "email", "phone", "password", "admin_role", "mfa_method", "security_policy_acceptance"),
    }[role]
    _require_signup_fields(payload, required)
    if role == "platform-admin" and not invitation:
        raise HTTPException(status_code=422, detail="A valid single-use invitation is required")
    if role in PROFESSIONAL_SIGNUP_TYPES:
        method = str(payload.data.get("onboarding_method") or ("INVITATION" if invitation else "JOIN_REQUEST"))
        if method not in {"INVITATION", "JOIN_REQUEST"}:
            raise HTTPException(status_code=422, detail="Choose a hospital invitation or membership request")
        if method == "INVITATION" and not invitation:
            raise HTTPException(status_code=422, detail="A valid single-use hospital invitation is required")
        if method == "JOIN_REQUEST":
            _require_signup_fields(payload, ("registered_hospital_id", "department_id", "employment_type", "employee_number"))
    if role == "government" and not invitation and not payload.data.get("authorization_document_key"):
        raise HTTPException(status_code=422, detail="A valid invitation or authorization document is required")
    if role == "government":
        email = str(payload.data.get("official_email", payload.email or "")).lower()
        if any(domain in email for domain in ("gmail.com", "yahoo.com", "outlook.com")):
            raise HTTPException(status_code=422, detail="Government applications require an official domain email")
    if role == "platform-admin":
        requested_role = payload.data.get("admin_role")
        if requested_role not in ADMINISTRATOR_ROLES:
            raise HTTPException(status_code=422, detail="Unsupported administrator role")
        invitation_limit = invitation.intended_role if invitation else None
        if invitation_limit in ADMINISTRATOR_ROLES and requested_role != invitation_limit:
            raise HTTPException(status_code=422, detail="Requested administrator role exceeds the invitation scope")


async def _create_signup(role: str, payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession) -> SignupApplicationResponse:
    invitation = await _validated_invitation(session, role, payload.invitation_token, payload.email)
    _validate_signup(role, payload, invitation)
    destination_hospital = None
    department_id = None
    membership_role = None
    if role in PROFESSIONAL_SIGNUP_TYPES:
        if invitation:
            destination_hospital = invitation.hospital_id
            department_id = invitation.department_id
            membership_role = invitation.intended_role or invitation.permitted_role
        else:
            try:
                destination_hospital = uuid.UUID(str(payload.data.get("registered_hospital_id")))
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="Select a registered hospital")
            department_id = str(payload.data.get("department_id") or "").strip()
            membership_role = "nurse" if role == "nurse" else str(payload.data.get("staff_role") or "specialist").lower()
        if membership_role not in INVITATION_ROLES[role]:
            raise HTTPException(status_code=422, detail="The staff role is not permitted for this signup")
        hospital = await session.scalar(select(Tenant).where(Tenant.id == destination_hospital, Tenant.status == "ACTIVE"))
        department = await resolve_hospital_department(session, destination_hospital, department_id)
        if department:
            department_id = department.name
        if not hospital or not department:
            raise HTTPException(status_code=422, detail="Hospital or department is not registered and active")
    latitude, longitude = _signup_coordinates(payload.data) if role in {"hospital", "clinic", "pharmacy", "laboratory"} else (None, None)
    filters = [condition for condition in (SignupApplication.email == payload.email if payload.email else None, SignupApplication.phone == payload.phone if payload.phone else None) if condition is not None]
    if filters and await session.scalar(select(SignupApplication).where(SignupApplication.application_type == role, or_(*filters), SignupApplication.status.notin_(["REJECTED", "SUSPENDED"]))):
        raise HTTPException(status_code=409, detail="An active application already exists for this email or phone")
    if role == "patient" and await session.scalar(select(AuthAccount).where(or_(AuthAccount.email == payload.email, AuthAccount.phone == payload.phone))):
        raise HTTPException(status_code=409, detail="An account already exists for this email or phone")
    safe_payload = payload.model_dump(exclude={"password", "confirm_password", "invitation_token"})
    application = SignupApplication(reference=_signup_reference(), application_type=role, onboarding_type=SIGNUP_ONBOARDING_TYPES[role], status=SIGNUP_PENDING_STATUSES[role], email=payload.email or payload.data.get("official_email"), phone=payload.phone, country=payload.country, organization_name=payload.data.get("legal_name"), payload_json=json.dumps(safe_payload, default=str), password_hash=hash_password(payload.password) if payload.password else None, invitation_id=invitation.id if invitation else None, consent_version=payload.consent_version)
    session.add(application)
    await session.flush()
    for consent_type, accepted in (("TERMS", payload.accept_terms), ("PRIVACY", payload.accept_privacy), ("MARKETING", payload.marketing_consent)):
        session.add(ConsentRecord(signup_application_id=application.id, consent_type=consent_type, policy_version=payload.consent_version, accepted=accepted, ip_address=request.client.host if request.client else None))
    session.add(ApplicationReviewHistory(signup_application_id=application.id, previous_status=None, new_status=application.status))
    default_tenant_id = uuid.UUID(settings.default_tenant_id)
    if role == "patient" and not await session.get(Tenant, default_tenant_id):
        session.add(Tenant(id=default_tenant_id, name="SynaptiVerse", state_location="Nigeria", accepts_patients=True, status="ACTIVE"))
    if role == "patient" and settings.skip_phone_verification:
        data = json.loads(application.payload_json)
        date_of_birth = datetime.fromisoformat(data["data"]["date_of_birth"]) if data.get("data", {}).get("date_of_birth") else None
        duplicate_key = patient_duplicate_key(data.get("first_name", ""), data.get("last_name", ""), date_of_birth)
        if await session.scalar(select(PatientRegistry).where(PatientRegistry.duplicate_key == duplicate_key).limit(1)):
            raise HTTPException(status_code=409, detail="A matching patient identity already exists and requires duplicate review")
        account = AuthAccount(tenant_id=uuid.UUID(settings.default_tenant_id), role="patient", identifier=application.phone, password_hash=application.password_hash, first_name=data.get("first_name", ""), last_name=data.get("last_name", ""), phone=application.phone, email=application.email, date_of_birth=date_of_birth, gender=data.get("data", {}).get("gender"), state=data.get("region"), lga=data.get("data", {}).get("city"), emergency_contact=data.get("data", {}).get("emergency_contact_phone"), hmo_provider=data.get("data", {}).get("hmo_provider"), blood_group=data.get("data", {}).get("blood_group"), genotype=data.get("data", {}).get("genotype"), known_allergies=data.get("data", {}).get("known_allergies"), current_medications=data.get("data", {}).get("current_medications"), card_number=f"SV-{secrets.token_hex(5).upper()}", phone_verified_at=utc_now(), is_active=True)
        session.add(account)
        await session.flush()
        if settings.supabase_auth_enabled:
            try:
                account.supabase_user_id = await provision_user(email=account.email, phone=account.phone, password=payload.password, metadata={"role": account.role, "application_id": str(application.id)})
            except SupabaseAuthError as exc:
                raise HTTPException(status_code=502, detail="Supabase Auth could not create the account") from exc
        await ensure_patient_registry(session, account)
        application.account_id, application.status = account.id, "ACTIVE"
        session.add(ApplicationReviewHistory(signup_application_id=application.id, previous_status="PHONE_VERIFICATION_REQUIRED", new_status="ACTIVE"))
    elif role == "patient":
        verification_code = f"{secrets.randbelow(1_000_000):06d}"
        session.add(VerificationEvent(signup_application_id=application.id, event_type="PHONE_OTP", status="PENDING", token_hash=token_hash(verification_code), expires_at=utc_now() + timedelta(minutes=10)))
        session.add(OutboxEvent(
            tenant_id=uuid.UUID(settings.default_tenant_id),
            aggregate_type="SignupApplication",
            aggregate_id=application.id,
            event_type="patient.phone_verification_requested",
            recipient_user_id=None,
            payload_json=json.dumps({
                "channel": "SMS",
                "recipient": payload.phone,
                "message": f"Your ClinicalFlow verification code is {verification_code}. It expires in 10 minutes.",
                "subject": "ClinicalFlow phone verification",
            }),
            classification="RESTRICTED",
            status="PENDING",
        ))
    if role in ORGANIZATION_SIGNUP_TYPES:
        session.add(OrganizationApplication(signup_application_id=application.id, legal_name=payload.data.get("legal_name", ""), registration_number=payload.data.get("registration_number"), licence_number=payload.data.get("licence_number") or payload.data.get("accreditation_number"), regulatory_authority=payload.data.get("regulatory_authority"), latitude=latitude, longitude=longitude, verification_status=application.status))
    if role in PROFESSIONAL_SIGNUP_TYPES:
        expiration = payload.data.get("licence_expiration")
        expires_at = datetime.fromisoformat(expiration) if expiration else None
        if expires_at and expires_at.replace(tzinfo=UTC) <= utc_now():
            raise HTTPException(status_code=422, detail="Professional licence is expired")
        session.add(ProfessionalCredential(signup_application_id=application.id, licence_number=payload.data["licence_number"], licensing_authority=payload.data["licensing_authority"], jurisdiction=payload.data["licence_jurisdiction"], specialty=payload.data.get("primary_specialty") or payload.data.get("nursing_category"), expires_at=expires_at))
        if not payload.password or not payload.email or not destination_hospital or not department_id or not membership_role:
            raise HTTPException(status_code=422, detail="Staff account or membership information is incomplete")
        if await session.scalar(select(AuthAccount).where(or_(AuthAccount.email == payload.email, AuthAccount.phone == payload.phone))):
            raise HTTPException(status_code=409, detail="A personal account already exists for this email or phone")
        name_parts = (payload.full_name or "").strip().split(maxsplit=1)
        account = AuthAccount(tenant_id=uuid.UUID(settings.default_tenant_id), role=membership_role, identifier=payload.email, password_hash=hash_password(payload.password), first_name=name_parts[0], last_name=name_parts[1] if len(name_parts) > 1 else "", phone=payload.phone, email=payload.email, specialty=payload.data.get("primary_specialty") if role == "specialist" else None, is_active=False)
        session.add(account)
        await session.flush()
        if settings.supabase_auth_enabled:
            try:
                account.supabase_user_id = await provision_user(email=account.email, phone=account.phone, password=payload.password, metadata={"role": account.role, "application_id": str(application.id)})
            except SupabaseAuthError as exc:
                raise HTTPException(status_code=502, detail="Supabase Auth could not create the account") from exc
        provider_registry = await ensure_provider_registry(session, account)
        provider_registry.licence_jurisdiction = payload.data.get("licence_jurisdiction")
        provider_registry.licence_number = payload.data.get("licence_number")
        provider_registry.verification_status = "PENDING_VERIFICATION"
        specialty_id = invitation.specialty_id if invitation and invitation.specialty_id else (payload.data.get("primary_specialty") if role == "specialist" else payload.data.get("nursing_focus"))
        membership = StaffMembership(user_id=account.id, hospital_id=destination_hospital, department_id=department_id, department_ref_id=department.id if department else None, role=membership_role, specialty_id=specialty_id, professional_license_number=payload.data.get("licence_number"), verification_status="PENDING_HOSPITAL_APPROVAL", employment_status="PENDING", is_active=False, is_on_duty=False, active_from=utc_now())
        session.add(membership)
        application.account_id = account.id
        if invitation:
            invitation.accepted_at = utc_now()
    for document in payload.data.get("documents", []):
        if not isinstance(document, dict) or not document.get("private_storage_key") or str(document.get("private_storage_key")).startswith(("http://", "https://")):
            raise HTTPException(status_code=422, detail="Verification documents must use private storage keys")
        if document.get("content_type") not in {"application/pdf", "image/jpeg", "image/png"} or not 1 <= int(document.get("size_bytes", 0)) <= 10_000_000:
            raise HTTPException(status_code=422, detail="Verification document type or size is not allowed")
        session.add(VerificationDocument(signup_application_id=application.id, document_type=document.get("document_type", "OTHER"), private_storage_key=document["private_storage_key"], original_name=document.get("original_name", "document"), content_type=document["content_type"], size_bytes=int(document["size_bytes"])))
    issued = None
    if application.status == "ACTIVE" and application.account_id:
        account = await session.get(AuthAccount, application.account_id)
        if account:
            issued = await create_session(session, account, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    await session.commit()
    if issued:
        response.set_cookie(ACCESS_COOKIE, issued.access_token, httponly=True, samesite="lax", secure=settings.environment == "production")
        response.set_cookie(REFRESH_COOKIE, issued.refresh_token, httponly=True, samesite="lax", secure=settings.environment == "production")
    return SignupApplicationResponse(id=application.id, reference=application.reference, application_type=role, onboarding_type=application.onboarding_type, status=application.status, submitted_at=application.submitted_at, login_path=SIGNUP_LOGIN_PATHS[role], dashboard_path=SIGNUP_DASHBOARD_PATHS[role] if application.status == "ACTIVE" else None)

@router.post("/signup/patient", response_model=SignupApplicationResponse, status_code=201)
async def signup_patient(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("patient", payload, request, response, session)

@router.post("/signup/specialist", response_model=SignupApplicationResponse, status_code=201)
async def signup_specialist(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("specialist", payload, request, response, session)

@router.post("/signup/hospital", response_model=SignupApplicationResponse, status_code=201)
async def signup_hospital(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("hospital", payload, request, response, session)

@router.post("/signup/clinic", response_model=SignupApplicationResponse, status_code=201)
async def signup_clinic(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("clinic", payload, request, response, session)

@router.post("/signup/nurse", response_model=SignupApplicationResponse, status_code=201)
async def signup_nurse(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("nurse", payload, request, response, session)

@router.post("/signup/pharmacy", response_model=SignupApplicationResponse, status_code=201)
async def signup_pharmacy(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("pharmacy", payload, request, response, session)

@router.post("/signup/laboratory", response_model=SignupApplicationResponse, status_code=201)
async def signup_laboratory(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("laboratory", payload, request, response, session)

@router.post("/signup/hmo", response_model=SignupApplicationResponse, status_code=201)
async def signup_hmo(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("hmo", payload, request, response, session)

@router.post("/signup/government", response_model=SignupApplicationResponse, status_code=201)
async def signup_government(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("government", payload, request, response, session)

@router.post("/signup/platform-admin", response_model=SignupApplicationResponse, status_code=201)
async def signup_platform_admin(payload: SignupApplicationCreate, request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _create_signup("platform-admin", payload, request, response, session)

@router.post("/hospital/staff-invitations", status_code=201)
async def create_staff_invitation(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, workspace, _tenant = await require_hospital_membership(request, session, roles={"hospital_admin", "department_coordinator"})
    payload = await request.json()
    department_id = str(payload.get("department_id") or "").strip()
    intended_role = str(payload.get("role") or "").strip().lower()
    if intended_role not in {"doctor", "specialist", "nurse"}:
        raise HTTPException(status_code=422, detail="Role must be doctor, specialist, or nurse")
    if intended_role in {"doctor", "specialist"} and not str(payload.get("specialty_id") or "").strip():
        raise HTTPException(status_code=422, detail="A specialty is required for doctors and specialists")
    if workspace.role == "department_coordinator" and department_id != workspace.department_id:
        raise HTTPException(status_code=403, detail="Coordinators may invite staff only to their own department")
    department = await resolve_hospital_department(session, workspace.hospital_id, department_id)
    if department:
        department_id = department.name
    if not department:
        raise HTTPException(status_code=422, detail="Select an active hospital department")
    email = str(payload.get("email") or "").strip().lower() or None
    phone = str(payload.get("phone") or "").strip() or None
    if not email and not phone:
        raise HTTPException(status_code=422, detail="An invited email or phone number is required")
    raw_token = secrets.token_urlsafe(32)
    expires_in_days = max(1, min(int(payload.get("expires_in_days") or 7), 30))
    invitation = StaffInvitation(hospital_id=workspace.hospital_id, organization_id=workspace.hospital_id, department_id=department_id, permitted_role=intended_role, intended_role=intended_role, specialty_id=str(payload.get("specialty_id") or "").strip() or None, employment_type=str(payload.get("employment_type") or "").strip() or None, invitation_code=f"staff-{secrets.token_hex(8)}", token_hash=token_hash(raw_token), invited_email=email, invited_phone=phone, expires_at=utc_now() + timedelta(days=expires_in_days), created_by_account_id=account.id, invited_by=account.id)
    session.add(invitation)
    await session.commit()
    return {"id": str(invitation.id), "invite_token": raw_token, "signup_path": f"/signup/{'nurse' if intended_role == 'nurse' else 'specialist'}?invite={raw_token}", "expires_at": invitation.expires_at}


@router.get("/hospital/staff-membership-requests")
async def list_staff_membership_requests(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, workspace, _tenant = await require_hospital_membership(request, session, roles={"hospital_admin", "department_coordinator"})
    query = select(StaffMembership, AuthAccount).join(AuthAccount, AuthAccount.id == StaffMembership.user_id).where(StaffMembership.hospital_id == workspace.hospital_id, StaffMembership.verification_status == "PENDING_HOSPITAL_APPROVAL")
    if workspace.role == "department_coordinator":
        query = query.where(StaffMembership.department_id == workspace.department_id)
    rows = (await session.execute(query.order_by(StaffMembership.created_at))).all()
    return {"items": [{"id": str(membership.id), "name": f"{account.first_name} {account.last_name}".strip(), "email": account.email, "department_id": membership.department_id, "role": membership.role, "specialty_id": membership.specialty_id, "created_at": membership.created_at} for membership, account in rows]}


@router.patch("/hospital/staff-membership-requests/{membership_id}")
async def review_staff_membership_request(membership_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    reviewer, workspace, _tenant = await require_hospital_membership(request, session, roles={"hospital_admin", "department_coordinator"})
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=422, detail="Decision must be APPROVE or REJECT")
    membership = await session.scalar(select(StaffMembership).where(StaffMembership.id == membership_id, StaffMembership.hospital_id == workspace.hospital_id).with_for_update())
    if not membership or (workspace.role == "department_coordinator" and membership.department_id != workspace.department_id):
        raise HTTPException(status_code=404, detail="Membership request not found in this workspace")
    account = await session.get(AuthAccount, membership.user_id)
    application = await session.scalar(select(SignupApplication).where(SignupApplication.account_id == membership.user_id).order_by(SignupApplication.submitted_at.desc()))
    if decision == "APPROVE":
        membership.verification_status, membership.employment_status, membership.is_active = "VERIFIED", "ACTIVE", True
        if account: account.is_active = True
        if application:
            previous_status = application.status
            application.status = "ACTIVE"
    else:
        membership.verification_status, membership.employment_status, membership.is_active = "REJECTED", "REJECTED", False
        if application:
            previous_status = application.status
            application.status = "REJECTED"
    if application:
        session.add(ApplicationReviewHistory(signup_application_id=application.id, reviewer_account_id=reviewer.id, previous_status=previous_status, new_status=application.status, internal_notes=str(payload.get("reason") or "") or None))
    await session.commit()
    return {"id": str(membership.id), "verification_status": membership.verification_status, "employment_status": membership.employment_status, "is_active": membership.is_active}

@router.get("/signup/registered-hospitals")
async def registered_signup_hospitals(session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    rows = (await session.execute(select(Tenant).join(HospitalDepartment, HospitalDepartment.hospital_id == Tenant.id).where(Tenant.status == "ACTIVE", HospitalDepartment.status == "ACTIVE").distinct().order_by(Tenant.name))).scalars().all()
    return {"items": [{"id": str(item.id), "name": item.name, "location": item.state_location} for item in rows]}


@router.get("/signup/registered-hospitals/{hospital_id}/departments")
async def registered_signup_departments(hospital_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    hospital = await session.scalar(select(Tenant).where(Tenant.id == hospital_id, Tenant.status == "ACTIVE"))
    if not hospital:
        raise HTTPException(status_code=404, detail="Registered hospital not found")
    rows = (await session.execute(select(HospitalDepartment).where(HospitalDepartment.hospital_id == hospital_id, HospitalDepartment.status == "ACTIVE").order_by(HospitalDepartment.name))).scalars().all()
    return {"items": [{"id": str(item.id), "name": item.name, "code": item.code} for item in rows]}


@router.post("/signup/invitations/validate")
async def validate_signup_invitation(payload: SignupInvitationValidateRequest, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    invitation = await _validated_invitation(session, payload.role, payload.token, payload.email)
    assert invitation is not None
    hospital = await session.get(Tenant, invitation.hospital_id)
    return {"valid": True, "organization_id": str(invitation.organization_id or invitation.hospital_id), "hospital_name": hospital.name if hospital else None, "department_id": invitation.department_id, "intended_role": invitation.intended_role or invitation.permitted_role, "specialty_id": invitation.specialty_id, "employment_type": invitation.employment_type, "expires_at": invitation.expires_at}

async def _verify_patient(payload: SignupVerificationRequest, session: AsyncSession, event_type: str, response: Response | None = None) -> SignupApplicationResponse:
    application = await session.get(SignupApplication, payload.application_id)
    if not application or application.application_type != "patient":
        raise HTTPException(status_code=404, detail="Signup application not found")
    event = await session.scalar(select(VerificationEvent).where(VerificationEvent.signup_application_id == application.id, VerificationEvent.event_type == event_type, VerificationEvent.status == "PENDING").order_by(VerificationEvent.created_at.desc()))
    if not event or not event.token_hash or event.token_hash != token_hash(payload.code) or (event.expires_at and event.expires_at.replace(tzinfo=UTC) <= utc_now()):
        raise HTTPException(status_code=422, detail="Verification code is invalid or expired")
    data = json.loads(application.payload_json)
    if not application.password_hash or not application.phone:
        raise HTTPException(status_code=422, detail="Patient application is incomplete")
    date_of_birth = datetime.fromisoformat(data["data"]["date_of_birth"]) if data.get("data", {}).get("date_of_birth") else None
    duplicate_key = patient_duplicate_key(data.get("first_name", ""), data.get("last_name", ""), date_of_birth)
    duplicate = await session.scalar(select(PatientRegistry).where(PatientRegistry.duplicate_key == duplicate_key).limit(1))
    if duplicate:
        raise HTTPException(status_code=409, detail="A matching patient identity already exists and requires duplicate review")
    account = AuthAccount(tenant_id=uuid.UUID(settings.default_tenant_id), role="patient", identifier=application.phone, password_hash=application.password_hash, first_name=data.get("first_name", ""), last_name=data.get("last_name", ""), phone=application.phone, email=application.email, date_of_birth=date_of_birth, gender=data.get("data", {}).get("gender"), state=data.get("region"), lga=data.get("data", {}).get("city"), emergency_contact=data.get("data", {}).get("emergency_contact_phone"), hmo_provider=data.get("data", {}).get("hmo_provider"), blood_group=data.get("data", {}).get("blood_group"), genotype=data.get("data", {}).get("genotype"), known_allergies=data.get("data", {}).get("known_allergies"), current_medications=data.get("data", {}).get("current_medications"), card_number=f"SV-{secrets.token_hex(5).upper()}", phone_verified_at=utc_now(), is_active=True)
    session.add(account)
    await session.flush()
    await ensure_patient_registry(session, account)
    application.account_id, application.status = account.id, "ACTIVE"
    event.status, event.completed_at = "VERIFIED", utc_now()
    for consent in (await session.execute(select(ConsentRecord).where(ConsentRecord.signup_application_id == application.id))).scalars().all():
        consent.account_id = account.id
    session.add(ApplicationReviewHistory(signup_application_id=application.id, previous_status="PHONE_VERIFICATION_REQUIRED", new_status="ACTIVE"))
    issued = await create_session(session, account)
    await session.commit()
    if response is not None:
        response.set_cookie(ACCESS_COOKIE, issued.access_token, httponly=True, samesite="lax", secure=settings.environment == "production")
        response.set_cookie(REFRESH_COOKIE, issued.refresh_token, httponly=True, samesite="lax", secure=settings.environment == "production")
    return SignupApplicationResponse(id=application.id, reference=application.reference, application_type="patient", onboarding_type=application.onboarding_type, status="ACTIVE", submitted_at=application.submitted_at, login_path="/login", dashboard_path="/dashboard")

@router.post("/signup/verify-phone", response_model=SignupApplicationResponse)
async def verify_signup_phone(payload: SignupVerificationRequest, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _verify_patient(payload, session, "PHONE_OTP", response)

@router.post("/signup/resend-phone", status_code=202)
async def resend_signup_phone(payload: SignupVerificationRequest, session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    application = await session.get(SignupApplication, payload.application_id)
    if not application or application.application_type != "patient" or application.status != "PHONE_VERIFICATION_REQUIRED":
        raise HTTPException(status_code=404, detail="Phone verification application not found")
    code = f"{secrets.randbelow(1_000_000):06d}"
    pending = (await session.execute(select(VerificationEvent).where(VerificationEvent.signup_application_id == application.id, VerificationEvent.event_type == "PHONE_OTP", VerificationEvent.status == "PENDING"))).scalars().all()
    for event in pending:
        event.status = "REPLACED"
    session.add(VerificationEvent(signup_application_id=application.id, event_type="PHONE_OTP", status="PENDING", token_hash=token_hash(code), expires_at=utc_now() + timedelta(minutes=10)))
    session.add(OutboxEvent(tenant_id=uuid.UUID(settings.default_tenant_id), aggregate_type="SignupApplication", aggregate_id=application.id, event_type="patient.phone_verification_requested", recipient_user_id=None, payload_json=json.dumps({"channel": "SMS", "recipient": application.phone, "message": f"Your ClinicalFlow verification code is {code}. It expires in 10 minutes.", "subject": "ClinicalFlow phone verification"}), classification="RESTRICTED", status="PENDING"))
    await session.commit()
    return {"status": "queued"}

@router.post("/signup/verify-email", response_model=SignupApplicationResponse)
async def verify_signup_email(payload: SignupVerificationRequest, response: Response, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    return await _verify_patient(payload, session, "EMAIL_OTP", response)

@router.get("/signup/status/{application_id}", response_model=SignupApplicationResponse)
async def signup_status(application_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> SignupApplicationResponse:
    application = await session.get(SignupApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Signup application not found")
    return SignupApplicationResponse(id=application.id, reference=application.reference, application_type=application.application_type, onboarding_type=application.onboarding_type, status=application.status, submitted_at=application.submitted_at, login_path=SIGNUP_LOGIN_PATHS[application.application_type], dashboard_path=SIGNUP_DASHBOARD_PATHS[application.application_type] if application.status == "ACTIVE" else None)


@router.patch("/platform/signup-applications/{application_id}/review")
async def review_signup_application(application_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    reviewer = await require_roles(request, session, ADMINISTRATOR_ROLES | {"admin"})
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=422, detail="Decision must be APPROVE or REJECT")
    application = await session.scalar(select(SignupApplication).where(SignupApplication.id == application_id).with_for_update())
    if not application or application.application_type not in ORGANIZATION_SIGNUP_TYPES:
        raise HTTPException(status_code=404, detail="Organization application not found")
    organization = await session.scalar(select(OrganizationApplication).where(OrganizationApplication.signup_application_id == application.id).with_for_update())
    if not organization:
        raise HTTPException(status_code=422, detail="Organization verification record is missing")
    previous_status = application.status
    if decision == "REJECT":
        application.status = "REJECTED"
        organization.verification_status = "REJECTED"
        session.add(ApplicationReviewHistory(signup_application_id=application.id, reviewer_account_id=reviewer.id, previous_status=previous_status, new_status=application.status, internal_notes=str(payload.get("reason") or "") or None))
        await session.commit()
        return {"id": str(application.id), "status": application.status, "tenant_id": None, "admin_account_id": None}
    if application.status == "ACTIVE" and application.account_id:
        admin = await session.get(AuthAccount, application.account_id)
        return {"id": str(application.id), "status": application.status, "tenant_id": str(admin.tenant_id) if admin else None, "admin_account_id": str(application.account_id)}
    data = json.loads(application.payload_json).get("data", {})
    admin_email = str(data.get("official_email") or application.email or "").strip().lower()
    if not admin_email or not application.password_hash:
        raise HTTPException(status_code=422, detail="Approved organizations require administrator email and password")
    existing = await session.scalar(select(AuthAccount).where(func.lower(AuthAccount.identifier) == admin_email))
    if existing:
        raise HTTPException(status_code=409, detail="Administrator account already exists")
    tenant = Tenant(name=organization.legal_name, state_location=str(data.get("jurisdiction") or data.get("state") or application.country), latitude=organization.latitude, longitude=organization.longitude, accepts_patients=application.application_type in {"hospital", "clinic"}, status="ACTIVE")
    session.add(tenant)
    await session.flush()
    facility = await ensure_facility_registry(session, tenant)
    facility.facility_type = {"clinic": "CLINIC", "pharmacy": "PHARMACY", "laboratory": "LABORATORY", "hmo": "PAYER", "government": "GOVERNMENT"}.get(application.application_type, "HOSPITAL")
    facility.country = application.country
    facility.jurisdiction = tenant.state_location
    facility.status = "ACTIVE"
    facility.accepts_patients = tenant.accepts_patients
    department_name = str(payload.get("default_department") or "Administration").strip() or "Administration"
    department = HospitalDepartment(hospital_id=tenant.id, name=department_name, code=f"ADMIN-{tenant.id.hex[:8].upper()}", status="ACTIVE")
    session.add(department)
    name_parts = str(data.get("administrator_name") or data.get("full_name") or "Facility Administrator").strip().split(maxsplit=1)
    admin_role = "hospital_admin" if application.application_type in {"hospital", "clinic"} else "admin"
    admin = AuthAccount(tenant_id=tenant.id, role=admin_role, identifier=admin_email, password_hash=application.password_hash, first_name=name_parts[0], last_name=name_parts[1] if len(name_parts) > 1 else "", email=admin_email, is_active=True, email_verified_at=utc_now())
    session.add(admin)
    await session.flush()
    membership = StaffMembership(user_id=admin.id, hospital_id=tenant.id, department_id=department.name, department_ref_id=department.id, role=admin_role, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=utc_now())
    session.add(membership)
    application.account_id = admin.id
    application.status = "ACTIVE"
    organization.verification_status = "VERIFIED"
    session.add(ApplicationReviewHistory(signup_application_id=application.id, reviewer_account_id=reviewer.id, previous_status=previous_status, new_status=application.status, internal_notes=str(payload.get("reason") or "") or None))
    await session.commit()
    return {"id": str(application.id), "status": application.status, "tenant_id": str(tenant.id), "admin_account_id": str(admin.id), "membership_id": str(membership.id)}

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
    return []

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
        department_id=appointment.department_id,
        ticket_id=appointment.ticket_id,
        doctor_id=appointment.doctor_id,
        staff_membership_id=appointment.staff_membership_id,
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
    authorization = request.headers.get("authorization", "")
    access_token = request.cookies.get(ACCESS_COOKIE) or (authorization[7:].strip() if authorization.lower().startswith("bearer ") else None)
    authenticated = await account_for_access_token(session, access_token) if access_token else None
    requester = authenticated[0] if authenticated else None
    owner_tenant_id = requester.tenant_id if requester and requester.role == "patient" else uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, owner_tenant_id)
    ticket = await session.scalar(select(Ticket).where(Ticket.id == payload.ticket_id, Ticket.customer_phone == payload.customer_phone).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found for this phone")
    destination_tenant_id = ticket_destination_id(ticket)
    specialty_id = ticket.assigned_specialty
    department_id = department_for_specialty(specialty_id)
    if not specialty_id:
        raise HTTPException(status_code=409, detail="Ticket has no triage specialty for doctor assignment")
    existing = await session.scalar(select(Appointment).where(Appointment.ticket_id == ticket.id, Appointment.status == "BOOKED"))
    if existing:
        raise HTTPException(status_code=409, detail="Ticket already has an appointment")

    await apply_tenant_context(session, destination_tenant_id)
    row = (await session.execute(
        select(ProviderSlot, Provider, AuthAccount, StaffMembership)
        .join(Provider, Provider.id == ProviderSlot.provider_id)
        .join(AuthAccount, AuthAccount.id == Provider.doctor_id)
        .join(
            StaffMembership,
            (StaffMembership.hospital_id == ProviderSlot.tenant_id)
            & (StaffMembership.user_id == AuthAccount.id)
            & (StaffMembership.specialty_id == Provider.specialty),
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
            StaffMembership.department_id == department_id,
            StaffMembership.role.in_(["doctor", "specialist"]),
            StaffMembership.is_active.is_(True),
            StaffMembership.is_on_duty.is_(True),
            StaffMembership.verification_status == "VERIFIED",
            StaffMembership.employment_status == "ACTIVE",
            StaffMembership.active_from <= ProviderSlot.starts_at,
            or_(StaffMembership.active_until.is_(None), StaffMembership.active_until >= ProviderSlot.starts_at),
        )
        .order_by(ProviderSlot.starts_at.asc(), Provider.full_name.asc())
        .with_for_update()
    )).first()
    if not row:
        ticket.queue_status = "AWAITING_CLINICAL_REVIEW"
        eligible_rows = list((await session.execute(
            select(AuthAccount, StaffMembership)
            .join(StaffMembership, StaffMembership.user_id == AuthAccount.id)
            .where(
                StaffMembership.hospital_id == destination_tenant_id,
                StaffMembership.department_id == department_id,
                StaffMembership.specialty_id == specialty_id,
                StaffMembership.role.in_(["doctor", "specialist", "department_coordinator"]),
                StaffMembership.is_active.is_(True),
                StaffMembership.is_on_duty.is_(True),
                StaffMembership.verification_status == "VERIFIED",
                StaffMembership.employment_status == "ACTIVE",
                AuthAccount.is_active.is_(True),
            )
        )).all())
        recipients = eligible_rows or [(None, None)]
        for recipient, recipient_membership in recipients:
            session.add(AppointmentAssignmentRequest(hospital_id=destination_tenant_id, department_id=department_id, ticket_id=ticket.id, recipient_user_id=recipient.id if recipient else None, recipient_membership_id=recipient_membership.id if recipient_membership else None, specialty_id=specialty_id, status="OPEN", expires_at=utc_now() + timedelta(minutes=15)))
            await create_appointment_notification(
                session,
                tenant_id=destination_tenant_id,
                recipient_account_id=recipient.id if recipient else None,
                recipient_role=(recipient_membership.role if recipient_membership else "department_coordinator"),
                appointment=None,
                ticket=ticket,
                event_type="APPOINTMENT_ASSIGNMENT_REQUESTED",
                title="Specialist review needed",
                body="No eligible verified on-duty clinician was available for the routed appointment slot.",
                payload={"ticket_id": str(ticket.id), "specialty_id": specialty_id, "hospital_id": str(destination_tenant_id), "department_id": department_id},
                recipient_membership_id=recipient_membership.id if recipient_membership else None,
                hospital_id=destination_tenant_id,
                department_id=department_id,
            )
        await session.commit()
        await broadcast_appointment_event(destination_tenant_id, "APPOINTMENT_ASSIGNMENT_REQUESTED", {"ticket_id": str(ticket.id), "specialty_id": specialty_id, "department_id": department_id})
        raise HTTPException(status_code=409, detail="No eligible verified on-duty clinician is available in the routed hospital department for this specialty and slot")
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
        await broadcast_appointment_event(destination_tenant_id, "appointment.reassignment_requested", {"ticket_id": str(ticket.id), "doctor_id": str(doctor.id), "specialty_id": specialty_id, "department_id": department_id})
        raise HTTPException(status_code=409, detail="Eligible doctor capacity has been reached at the routed hospital")

    slot.is_booked = True
    ticket.appointment_slot = slot.starts_at
    appointment = Appointment(
        tenant_id=destination_tenant_id,
        hospital_id=destination_tenant_id,
        department_id=department_id,
        ticket_id=ticket.id,
        doctor_id=doctor.id,
        staff_membership_id=membership.id,
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
    patient_account = requester if requester and requester.role == "patient" else await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
    patient_display_name = f"{patient_account.first_name} {patient_account.last_name}".strip() if patient_account else "Patient"
    response_payload = {
        "appointment_id": str(appointment.id),
        "ticket_id": str(ticket.id),
        "patient_phone": ticket.customer_phone,
        "patient_display_name": patient_display_name,
        "starts_at": slot.starts_at.isoformat(),
        "ends_at": slot.ends_at.isoformat(),
        "hospital_id": str(destination_tenant_id),
        "department_id": department_id,
        "doctor_id": str(doctor.id),
        "staff_membership_id": str(membership.id),
        "specialty_id": membership.specialty_id,
        "urgency": ticket.urgency_level,
        "room_label": provider.room_label,
        "actions": ["view", "accept", "request_reassignment"],
    }
    doctor_notification = await create_appointment_notification(
        session,
        tenant_id=destination_tenant_id,
        recipient_account_id=doctor.id,
        recipient_role="doctor",
        appointment=appointment,
        ticket=ticket,
        event_type="APPOINTMENT_ASSIGNED",
        title="New appointment assigned",
        body=f"Patient: {patient_display_name}. Date: {slot.starts_at:%d %B %Y}. Time: {slot.starts_at:%I:%M %p}. Department: {department_id}. Urgency: {ticket.urgency_level}. Room: {provider.room_label}.",
        payload=response_payload,
        recipient_membership_id=membership.id,
        hospital_id=destination_tenant_id,
        department_id=department_id,
    )
    await create_appointment_notification(
        session,
        tenant_id=ticket.tenant_id,
        recipient_account_id=patient_account.id if patient_account else None,
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
    await broadcast_appointment_event(destination_tenant_id, "APPOINTMENT_ASSIGNED", response_payload, doctor.id, session=session, notification_id=doctor_notification.id)
    await broadcast_appointment_event(ticket.tenant_id, "appointment.created", response_payload, patient_account.id if patient_account else None)
    return response
@router.get("/appointments", response_model=list[AppointmentResponse])
async def staff_appointments(request: Request, session: AsyncSession = Depends(get_db)) -> list[AppointmentResponse]:
    account = await require_roles(request, session, {"specialist", "doctor", "nurse", "hospital_admin", "department_coordinator", "admin"})
    memberships = await active_staff_memberships(session, account)
    membership_ids = [membership.id for membership in memberships]
    workspace_pairs = {(membership.hospital_id, membership.department_id) for membership in memberships}
    if account.role in {"doctor", "specialist"}:
        query = select(Appointment).where(
            Appointment.hospital_id.in_([hospital_id for hospital_id, _department_id in workspace_pairs] or [account.tenant_id]),
            or_(Appointment.doctor_id == account.id, Appointment.staff_membership_id.in_(membership_ids) if membership_ids else False),
        )
    elif account.role == "nurse":
        if not workspace_pairs:
            raise HTTPException(status_code=403, detail="No verified active nurse workspace")
        query = select(Appointment).where(
            or_(*[Appointment.hospital_id == hospital_id for hospital_id, _department_id in workspace_pairs]),
            or_(*[Appointment.department_id == department_id for _hospital_id, department_id in workspace_pairs]),
            Appointment.status == "BOOKED",
        )
    elif account.role == "department_coordinator":
        if not workspace_pairs:
            raise HTTPException(status_code=403, detail="No verified active coordinator workspace")
        query = select(Appointment).where(
            or_(*[Appointment.hospital_id == hospital_id for hospital_id, _department_id in workspace_pairs]),
            or_(*[Appointment.department_id == department_id for _hospital_id, department_id in workspace_pairs]),
        )
    else:
        query = select(Appointment).where(Appointment.hospital_id == account.tenant_id)
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

@router.get("/registry/facilities")
async def registry_facilities(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    service_code = str(request.query_params.get("service_code") or "").strip()
    specialty_code = str(request.query_params.get("specialty_code") or "").strip()
    facility_type = str(request.query_params.get("facility_type") or "").strip().upper()
    emergency = str(request.query_params.get("emergency_capable") or "").lower()
    query = select(FacilityRegistry, Tenant).join(Tenant, Tenant.id == FacilityRegistry.tenant_id).where(
        FacilityRegistry.status == "ACTIVE",
        FacilityRegistry.accepts_patients.is_(True),
        Tenant.status == "ACTIVE",
        Tenant.accepts_patients.is_(True),
    )
    if facility_type:
        query = query.where(FacilityRegistry.facility_type == facility_type)
    if emergency in {"true", "1"}:
        query = query.where(FacilityRegistry.emergency_capable.is_(True))
    if service_code or specialty_code:
        query = query.join(FacilityService, FacilityService.facility_registry_id == FacilityRegistry.id).where(FacilityService.status == "ACTIVE")
        if service_code:
            query = query.where(FacilityService.service_code == service_code)
        if specialty_code:
            query = query.where(FacilityService.specialty_code == specialty_code)
    rows = (await session.execute(query.distinct().order_by(Tenant.name))).all()
    return {"items": [{"id": str(facility.id), "tenant_id": str(tenant.id), "name": tenant.name, "facility_type": facility.facility_type, "country": facility.country, "jurisdiction": facility.jurisdiction, "location": tenant.state_location, "latitude": tenant.latitude, "longitude": tenant.longitude, "emergency_capable": facility.emergency_capable, "capacity_status": facility.capacity_status} for facility, tenant in rows]}


@router.get("/registry/providers/{account_id}")
async def registry_provider(account_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse", "hospital_admin", "department_coordinator", "admin"})
    provider = await session.scalar(select(ProviderRegistry).where(ProviderRegistry.account_id == account_id))
    if not provider:
        target = await session.get(AuthAccount, account_id)
        if not target or target.role not in {"doctor", "specialist", "nurse", "lab", "pharmacy"}:
            raise HTTPException(status_code=404, detail="Provider registry record not found")
        provider = await ensure_provider_registry(session, target)
        await session.commit()
    memberships = list((await session.execute(select(StaffMembership).where(StaffMembership.user_id == account_id, StaffMembership.hospital_id == account.tenant_id))).scalars().all())
    return {"id": str(provider.id), "account_id": str(provider.account_id), "practitioner_identifier": provider.practitioner_identifier, "professional_role": provider.professional_role, "licence_jurisdiction": provider.licence_jurisdiction, "licence_number": provider.licence_number, "verification_status": provider.verification_status, "memberships": [{"id": str(item.id), "hospital_id": str(item.hospital_id), "department_id": item.department_id, "specialty_id": item.specialty_id, "status": item.verification_status} for item in memberships]}


@router.get("/patient/consents")
async def patient_consents(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    patient = await ensure_patient_registry(session, account)
    rows = list((await session.execute(select(PatientConsentDirective).where(PatientConsentDirective.patient_id == patient.id).order_by(PatientConsentDirective.purpose))).scalars().all())
    await session.commit()
    return {"items": [{"id": str(item.id), "purpose": item.purpose, "grantee_type": item.grantee_type, "grantee_id": str(item.grantee_id) if item.grantee_id else None, "status": item.status, "data_categories": json.loads(item.data_categories_json) if item.data_categories_json else [], "policy_version": item.policy_version, "granted_at": item.granted_at, "revoked_at": item.revoked_at} for item in rows]}


@router.patch("/patient/consents/{purpose}")
async def update_patient_consent(purpose: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    payload = await request.json()
    status = str(payload.get("status") or "").upper()
    if status not in {"ACTIVE", "WITHDRAWN"}:
        raise HTTPException(status_code=422, detail="Consent status must be ACTIVE or WITHDRAWN")
    patient = await ensure_patient_registry(session, account)
    directive = await session.scalar(select(PatientConsentDirective).where(PatientConsentDirective.patient_id == patient.id, PatientConsentDirective.purpose == purpose.upper(), PatientConsentDirective.grantee_type == "CARE_TEAM", PatientConsentDirective.grantee_id.is_(None)).with_for_update())
    if not directive:
        directive = PatientConsentDirective(patient_id=patient.id, purpose=purpose.upper(), grantee_type="CARE_TEAM", status=status, policy_version="2026-07")
        session.add(directive)
    directive.status = status
    directive.data_categories_json = json.dumps(payload.get("data_categories") or [])
    directive.revoked_at = utc_now() if status == "WITHDRAWN" else None
    if status == "ACTIVE":
        directive.granted_at = utc_now()
    await session.flush()
    session.add(ProvenanceRecord(tenant_id=account.tenant_id, resource_type="PatientConsentDirective", resource_id=directive.id, action=status, actor_account_id=account.id, source="PATIENT_PORTAL"))
    await session.commit()
    return {"id": str(directive.id), "purpose": directive.purpose, "status": directive.status}


@router.get("/patient/health-card")
async def patient_health_card(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    patient = await ensure_patient_registry(session, account)
    tenant = await session.get(Tenant, account.tenant_id)
    if tenant:
        await ensure_facility_registry(session, tenant)
    credential, raw_token = await issue_health_card_credential(session, account, patient)
    await session.commit()
    return {"card_number": account.card_number, "internal_patient_id": patient.internal_identifier, "issuer": tenant.name if tenant else None, "issued_at": credential.issued_at, "expires_at": credential.expires_at, "emergency_access_enabled": credential.emergency_access_enabled, "qr_payload": f"synaptiverse://health-card/{raw_token}"}


@router.post("/health-card/lookup")
async def health_card_lookup(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse"})
    payload = await request.json()
    raw_token = str(payload.get("token") or "").removeprefix("synaptiverse://health-card/").strip()
    if not raw_token:
        raise HTTPException(status_code=422, detail="A secure health-card token is required")
    credential = await session.scalar(select(HealthCardCredential).where(HealthCardCredential.token_hash == token_hash(raw_token), HealthCardCredential.status == "ACTIVE").limit(1))
    if not credential or (credential.expires_at and credential.expires_at.replace(tzinfo=UTC) <= utc_now()):
        raise HTTPException(status_code=404, detail="Health-card credential is invalid or expired")
    patient = await session.get(PatientRegistry, credential.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient registry record not found")
    membership = await require_staff_workspace(session, account, hospital_id=credential.issuer_facility_id, roles={"doctor", "specialist", "nurse"})
    consent = await session.scalar(select(PatientConsentDirective).where(PatientConsentDirective.patient_id == patient.id, PatientConsentDirective.purpose == "CARE_DELIVERY", PatientConsentDirective.status == "ACTIVE").limit(1))
    if not consent:
        session.add(ProvenanceRecord(tenant_id=membership.hospital_id, resource_type="HealthCardCredential", resource_id=credential.id, action="ACCESS_DENIED_CONSENT", actor_account_id=account.id, source="CLINICIAN_PORTAL"))
        await session.commit()
        raise HTTPException(status_code=403, detail="Patient consent does not permit health-card lookup")
    session.add(ProvenanceRecord(tenant_id=membership.hospital_id, resource_type="HealthCardCredential", resource_id=credential.id, action="LOOKED_UP", actor_account_id=account.id, source="CLINICIAN_PORTAL"))
    await session.commit()
    return {"patient_id": str(patient.id), "internal_patient_id": patient.internal_identifier, "name": f"{patient.first_name} {patient.last_name}".strip(), "date_of_birth": patient.date_of_birth, "card_number": credential.card_number.rsplit("-", 1)[0], "issuer_facility_id": str(credential.issuer_facility_id), "emergency_access_enabled": credential.emergency_access_enabled}

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
    report_rows = (await session.execute(
        select(DiagnosticReport, LaboratoryOrder, Tenant)
        .join(LaboratoryOrder, LaboratoryOrder.id == DiagnosticReport.order_id)
        .join(Tenant, Tenant.id == LaboratoryOrder.laboratory_id)
        .where(LaboratoryOrder.patient_id == account.id, DiagnosticReport.released_to_patient_at.is_not(None))
        .order_by(DiagnosticReport.released_to_patient_at.desc())
    )).all()
    events.extend(
        {"id": str(report.id), "type": "LAB_RESULT", "title": "Laboratory report", "summary": report.conclusion, "facility_name": laboratory.name, "status": report.status, "created_at": report.released_to_patient_at, "tone": "success"}
        for report, _order, laboratory in report_rows
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
        await create_appointment_notification(session, tenant_id=appointment.hospital_id, recipient_account_id=appointment.doctor_id, recipient_role="doctor", appointment=appointment, ticket=ticket, event_type="APPOINTMENT_CANCELLED", title="Appointment cancelled", body="An assigned appointment was cancelled.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id)}, recipient_membership_id=appointment.staff_membership_id, hospital_id=appointment.hospital_id, department_id=appointment.department_id)
        patient_account = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
        if patient_account:
            await create_appointment_notification(session, tenant_id=ticket.tenant_id, recipient_account_id=patient_account.id, recipient_role="patient", appointment=appointment, ticket=ticket, event_type="APPOINTMENT_CANCELLED", title="Appointment cancelled", body="Your appointment has been cancelled.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id)})
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
        await create_appointment_notification(session, tenant_id=appointment.hospital_id, recipient_account_id=appointment.doctor_id, recipient_role="doctor", appointment=appointment, ticket=ticket, event_type="APPOINTMENT_RESCHEDULED", title="Appointment rescheduled", body="An assigned appointment was rescheduled.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id), "starts_at": new_slot.starts_at.isoformat()}, recipient_membership_id=appointment.staff_membership_id, hospital_id=appointment.hospital_id, department_id=appointment.department_id)
        patient_account = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
        if patient_account:
            await create_appointment_notification(session, tenant_id=ticket.tenant_id, recipient_account_id=patient_account.id, recipient_role="patient", appointment=appointment, ticket=ticket, event_type="APPOINTMENT_RESCHEDULED", title="Appointment rescheduled", body=f"Your appointment was moved to {new_slot.starts_at:%d %B %Y at %I:%M %p}.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id), "starts_at": new_slot.starts_at.isoformat()})
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
    membership = await session.scalar(select(StaffMembership).where(
        StaffMembership.hospital_id == appointment.hospital_id,
        StaffMembership.department_id == appointment.department_id,
        StaffMembership.user_id == account.id,
        StaffMembership.role.in_(["doctor", "specialist"]),
        StaffMembership.specialty_id == appointment.specialty_id,
        StaffMembership.is_active.is_(True),
        StaffMembership.is_on_duty.is_(True),
        StaffMembership.verification_status == "VERIFIED",
        StaffMembership.employment_status == "ACTIVE",
    ))
    if not membership or not account.is_active or provider.specialty != appointment.specialty_id or slot.is_locked or slot.is_booked:
        raise HTTPException(status_code=403, detail="Doctor is not eligible to accept this appointment")
    appointment.doctor_id = account.id
    appointment.staff_membership_id = membership.id
    appointment.status = "BOOKED"
    slot.is_booked = True
    competing_requests = list((await session.execute(select(AppointmentAssignmentRequest).where(AppointmentAssignmentRequest.ticket_id == appointment.ticket_id, AppointmentAssignmentRequest.status == "OPEN").with_for_update())).scalars().all())
    for assignment_request in competing_requests:
        assignment_request.appointment_id = appointment.id
        assignment_request.status = "ACCEPTED" if assignment_request.recipient_user_id == account.id else "CLOSED"
        assignment_request.accepted_at = utc_now() if assignment_request.recipient_user_id == account.id else None
        assignment_request.closed_at = utc_now()
    ticket = await session.get(Ticket, appointment.ticket_id)
    if ticket:
        ticket.appointment_slot = appointment.starts_at or slot.starts_at
        doctor_notification = await create_appointment_notification(session, tenant_id=appointment.hospital_id, recipient_account_id=account.id, recipient_role="doctor", appointment=appointment, ticket=ticket, event_type="APPOINTMENT_ASSIGNED", title="New appointment assigned", body="This appointment is now assigned to you.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id), "department_id": appointment.department_id, "specialty_id": appointment.specialty_id}, recipient_membership_id=membership.id, hospital_id=appointment.hospital_id, department_id=appointment.department_id)
        patient_account = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
        if patient_account:
            await create_appointment_notification(session, tenant_id=ticket.tenant_id, recipient_account_id=patient_account.id, recipient_role="patient", appointment=appointment, ticket=ticket, event_type="APPOINTMENT_ASSIGNED", title="Appointment confirmed", body="A clinician has accepted your appointment.", payload={"appointment_id": str(appointment.id), "ticket_id": str(ticket.id)})
    await session.commit()
    response = await appointment_response(session, appointment)
    await broadcast_appointment_event(appointment.hospital_id, "APPOINTMENT_ASSIGNED", response.model_dump(), account.id, session=session, notification_id=doctor_notification.id)
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

async def persist_routing_decision(session: AsyncSession, ticket: TicketResponse, clinical_route: Any, candidates: tuple[Any, ...], selected_facility_id: uuid.UUID | None, preferred_facility_id: uuid.UUID | None, reason: str) -> RoutingDecision:
    decision = RoutingDecision(ticket_id=ticket.id, patient_owner_tenant_id=ticket.tenant_id, selected_facility_id=selected_facility_id, required_service=str(clinical_route.target_specialty), required_specialty=str(clinical_route.target_specialty), urgency=str(clinical_route.derived_urgency), status="SELECTED" if selected_facility_id else "NO_SUITABLE_FACILITY", selection_reason=reason, patient_preference_facility_id=preferred_facility_id)
    session.add(decision)
    await session.flush()
    session.add_all([RoutingCandidate(routing_decision_id=decision.id, facility_id=item.tenant.id, rank=item.rank, eligible=item.eligible, distance_km=item.distance_km, suitability_score=item.suitability_score, has_required_capability=item.has_required_capability, has_emergency_capability=item.has_emergency_capability, has_staff_coverage=item.has_staff_coverage, has_capacity=item.has_capacity, reasons_json=json.dumps(item.reasons)) for item in candidates])
    await session.commit()
    return decision


@router.post("/patient/triage")
async def patient_triage(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    payload = await request.json()
    symptom_text = str(payload.get("symptom_description") or "").strip()
    if len(symptom_text) < 3:
        raise HTTPException(status_code=422, detail="Describe the symptoms in a little more detail")
    latitude, longitude = patient_coordinates_from_payload(payload)
    preferred_id = None
    if payload.get("preferred_facility_id"):
        try: preferred_id = uuid.UUID(str(payload["preferred_facility_id"]))
        except ValueError: raise HTTPException(status_code=422, detail="Preferred facility identifier is invalid")
    clinical_route = await request.app.state.knowledge_graph.route(symptom_text)
    candidates = await rank_eligible_facilities(session, latitude, longitude, clinical_route, preferred_facility_id=preferred_id)
    route = await select_nearest_eligible_hospital(session, latitude, longitude, clinical_route, preferred_facility_id=preferred_id)
    ticket = await persist_ticket(TicketCreate(customer_phone=account.phone or "", raw_intake_text=symptom_text, channel="WEB"), request, session, clinical_route, account.tenant_id, route.tenant.id if route else None, latitude, longitude, route.distance_km if route else None, route_attempted=True)
    if not route:
        reason = "No registered facility met the clinical capability, staffing, emergency, capacity, and intake requirements"
        await persist_routing_decision(session, ticket, clinical_route, candidates, None, preferred_id, reason)
        message = "No suitable registered facility is available. Seek immediate local emergency care." if clinical_route.derived_urgency == "CRITICAL" else "No suitable registered facility is available. A care coordinator must review this ticket."
        raise HTTPException(status_code=503, detail={"code": "NO_SUITABLE_FACILITY", "message": message, "ticket_id": str(ticket.id), "urgency": clinical_route.derived_urgency})
    await persist_routing_decision(session, ticket, clinical_route, candidates, route.tenant.id, preferred_id, route.match_basis)
    slot_payload = None
    if route.slot and route.provider:
        slot_payload = {"slot_id": str(route.slot.id), "slot_start": route.slot.starts_at.isoformat(), "slot_end": route.slot.ends_at.isoformat(), "specialist_name": route.provider.full_name, "specialty": route.provider.specialty, "room_label": route.provider.room_label}
    alternatives = sorted((item for item in candidates if item.eligible and item.tenant.id != route.tenant.id), key=lambda item: item.rank or 999999)[:3]
    selected_candidate = next(item for item in candidates if item.tenant.id == route.tenant.id)
    return {"condition_name": clinical_route.condition_id.replace("_", " ").title(), "possible_illness": possible_illness_for_route(clinical_route.condition_id, clinical_route.symptom_ids), "diagnosis_disclaimer": "This is not a diagnosis. A qualified clinician must confirm what illness you have.", "urgency": clinical_route.derived_urgency, "specialty": clinical_route.target_specialty, "required_department": department_for_specialty(clinical_route.target_specialty), "severity": severity_for_urgency(clinical_route.derived_urgency), "severity_label": severity_for_urgency(clinical_route.derived_urgency).title(), "severity_message": severity_message_for_urgency(clinical_route.derived_urgency), "messages": [f"I identified: {', '.join(clinical_route.symptom_ids) or 'no exact symptom match'}.", f"Routing source: {clinical_route.source}."], "nearest_clinic": {"tenant_id": str(route.tenant.id), "clinic_name": route.tenant.name, "address": route.tenant.state_location, "distance_km": round(route.distance_km, 2), "specialist_name": route.provider.full_name if route.provider else None, "match_basis": route.match_basis, "required_specialty": route.required_specialty, "emergency_capable": selected_candidate.has_emergency_capability}, "alternative_facilities": [{"tenant_id": str(item.tenant.id), "clinic_name": item.tenant.name, "address": item.tenant.state_location, "distance_km": round(item.distance_km or 0, 2), "match_basis": "; ".join(item.reasons[:2])} for item in alternatives], "appointment_slot": slot_payload, "ticket": {"id": str(ticket.id), "ticket_number": ticket.ticket_number}}


@router.get("/hospital/tickets/{ticket_id}/routing")
async def hospital_ticket_routing(ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    _account, workspace, _tenant = await require_hospital_membership(request, session)
    ticket = await session.scalar(select(Ticket).where(Ticket.id == ticket_id, ticket_visible_to_tenant(workspace.hospital_id)))
    decision = await session.scalar(select(RoutingDecision).where(RoutingDecision.ticket_id == ticket_id)) if ticket else None
    if not decision: raise HTTPException(status_code=404, detail="Routing decision not found in this workspace")
    rows = (await session.execute(select(RoutingCandidate, Tenant).join(Tenant, Tenant.id == RoutingCandidate.facility_id).where(RoutingCandidate.routing_decision_id == decision.id).order_by(RoutingCandidate.eligible.desc(), RoutingCandidate.rank.asc()))).all()
    return {"ticket_id": str(ticket_id), "selected_facility_id": str(decision.selected_facility_id) if decision.selected_facility_id else None, "required_service": decision.required_service, "required_specialty": decision.required_specialty, "urgency": decision.urgency, "status": decision.status, "selection_reason": decision.selection_reason, "manual_override_reason": decision.manual_override_reason, "candidates": [{"facility_id": str(item.facility_id), "facility_name": tenant.name, "eligible": item.eligible, "rank": item.rank, "distance_km": item.distance_km, "score": item.suitability_score, "reasons": json.loads(item.reasons_json)} for item, tenant in rows]}


@router.patch("/hospital/tickets/{ticket_id}/routing")
async def override_ticket_routing(ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, workspace, _tenant = await require_hospital_membership(request, session, roles={"hospital_admin", "department_coordinator"})
    payload = await request.json(); reason = str(payload.get("reason") or "").strip()
    if len(reason) < 10: raise HTTPException(status_code=422, detail="A specific manual routing reason is required")
    try: facility_id = uuid.UUID(str(payload.get("facility_id") or ""))
    except ValueError: raise HTTPException(status_code=422, detail="A valid destination facility is required")
    ticket = await session.scalar(select(Ticket).where(Ticket.id == ticket_id, ticket_visible_to_tenant(workspace.hospital_id)).with_for_update())
    decision = await session.scalar(select(RoutingDecision).where(RoutingDecision.ticket_id == ticket_id).with_for_update()) if ticket else None
    if not ticket or not decision: raise HTTPException(status_code=404, detail="Routing decision not found in this workspace")
    candidate = await session.scalar(select(RoutingCandidate).where(RoutingCandidate.routing_decision_id == decision.id, RoutingCandidate.facility_id == facility_id, RoutingCandidate.eligible.is_(True)))
    if not candidate: raise HTTPException(status_code=422, detail="Manual override destination is not an eligible clinical candidate")
    ticket.routed_tenant_id, ticket.route_distance_km = facility_id, candidate.distance_km
    decision.selected_facility_id, decision.status, decision.manual_override_reason = facility_id, "MANUALLY_OVERRIDDEN", reason
    decision.overridden_by_account_id, decision.overridden_at = account.id, utc_now()
    await write_audit_log(session, AuditAction.TICKET_ASSIGNED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(workspace.hospital_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="RoutingDecision", resource_id=str(decision.id), metadata={"ticket_id": str(ticket.id), "destination_facility_id": str(facility_id), "reason": reason})
    await session.commit()
    return {"ticket_id": str(ticket.id), "selected_facility_id": str(facility_id), "status": decision.status, "reason": reason}

@router.get("/appointments/assignment-requests")
async def list_assignment_requests(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_roles(request, session, {"doctor", "specialist", "department_coordinator"})
    memberships = await active_staff_memberships(session, account)
    membership_ids = [membership.id for membership in memberships]
    if not membership_ids:
        return []
    now = utc_now()
    requests = list((await session.execute(
        select(AppointmentAssignmentRequest)
        .where(
            AppointmentAssignmentRequest.recipient_user_id == account.id,
            AppointmentAssignmentRequest.recipient_membership_id.in_(membership_ids),
            AppointmentAssignmentRequest.status == "OPEN",
            AppointmentAssignmentRequest.expires_at > now,
        )
        .order_by(AppointmentAssignmentRequest.created_at.asc())
    )).scalars().all())
    return [
        {
            "id": str(assignment_request.id),
            "hospital_id": str(assignment_request.hospital_id),
            "department_id": assignment_request.department_id,
            "specialty_id": assignment_request.specialty_id,
            "status": assignment_request.status,
            "expires_at": assignment_request.expires_at,
            "created_at": assignment_request.created_at,
        }
        for assignment_request in requests
    ]

@router.get("/notifications")
async def notifications(request: Request, session: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    memberships = await active_staff_memberships(session, account) if account.role != "patient" else []
    membership_ids = [membership.id for membership in memberships]
    notification_filters = [Notification.recipient_user_id == account.id, Notification.recipient_account_id == account.id]
    if membership_ids:
        notification_filters.append(Notification.recipient_membership_id.in_(membership_ids))
    stored_notifications = list((await session.execute(
        select(Notification)
        .where(Notification.tenant_id.in_([membership.hospital_id for membership in memberships] or [account.tenant_id]), or_(*notification_filters))
        .order_by(Notification.created_at.desc())
        .limit(20)
    )).scalars().all())
    rows = [
        {
            "id": str(notification.id),
            "recipient_type": notification.recipient_role.upper(),
            "recipient_id": str(notification.recipient_user_id or notification.recipient_account_id) if (notification.recipient_user_id or notification.recipient_account_id) else None,
            "recipient_membership_id": str(notification.recipient_membership_id) if notification.recipient_membership_id else None,
            "hospital_id": str(notification.hospital_id) if notification.hospital_id else None,
            "department_id": notification.department_id,
            "title": notification.title,
            "body": notification.body or "",
            "priority": notification.priority,
            "is_read": notification.is_read,
            "read_at": notification.read_at,
            "acknowledged_at": notification.acknowledged_at,
            "requires_acknowledgement": notification.event_type in {
                "APPOINTMENT_ASSIGNED",
                "APPOINTMENT_REMINDER",
                "PATIENT_CHECKED_IN",
            },
            "ticket_id": str(notification.ticket_id) if notification.ticket_id else None,
            "appointment_id": str(notification.appointment_id) if notification.appointment_id else None,
            "type": notification.event_type.lower().replace("_", ".") if notification.event_type.startswith("APPOINTMENT_") else notification.event_type,
            "event_type": notification.event_type,
            "created_at": notification.created_at,
        }
        for notification in stored_notifications
    ]
    ticket_query = select(Ticket)
    if account.role == "patient":
        ticket_query = ticket_query.where(Ticket.customer_phone == account.phone)
    elif memberships:
        visible_pairs = {(membership.hospital_id, membership.department_id) for membership in memberships}
        ticket_query = ticket_query.where(
            or_(*[ticket_visible_to_tenant(hospital_id) for hospital_id, _department_id in visible_pairs]),
            or_(*[Ticket.assigned_specialty == department_id for _hospital_id, department_id in visible_pairs]),
        )
    else:
        ticket_query = ticket_query.where(False)
    tickets = list((await session.execute(ticket_query.order_by(Ticket.created_at.desc()).limit(20))).scalars().all())
    marker_prefix = f"{account.id}:"
    markers = list((await session.execute(select(OperationalRecord).where(OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == "notification", OperationalRecord.resource == "read", OperationalRecord.title.like(f"{marker_prefix}%")))).scalars().all())
    read_ids = {marker.title.removeprefix(marker_prefix) for marker in markers}
    rows.extend({"id": str(ticket.id), "recipient_type": "PATIENT" if account.role == "patient" else account.role.upper(), "recipient_id": str(account.id), "title": f"Queue update · {ticket.ticket_number}", "body": f"{ticket.queue_status.replace('_', ' ').title()} · {ticket.assigned_specialty or 'Front Desk'}", "is_read": str(ticket.id) in read_ids, "ticket_id": str(ticket.id), "urgency_level": ticket.urgency_level, "condition_name": ticket.matched_condition_id, "type": "QUEUE_UPDATE", "created_at": ticket.created_at} for ticket in tickets)
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)

async def mark_notification(session: AsyncSession, account: AuthAccount, notification_id: str) -> None:
    try:
        parsed_id = uuid.UUID(notification_id)
    except ValueError:
        parsed_id = None
    if parsed_id:
        memberships = await active_staff_memberships(session, account) if account.role != "patient" else []
        membership_ids = [membership.id for membership in memberships]
        filters = [Notification.recipient_user_id == account.id, Notification.recipient_account_id == account.id]
        if membership_ids:
            filters.append(Notification.recipient_membership_id.in_(membership_ids))
        notification = await session.scalar(select(Notification).where(Notification.id == parsed_id, or_(*filters)).with_for_update())
        if notification:
            notification.is_read = True
            notification.read_at = utc_now()
            return
    title = f"{account.id}:{notification_id}"
    exists = await session.scalar(select(OperationalRecord).where(OperationalRecord.tenant_id == account.tenant_id, OperationalRecord.entity == "notification", OperationalRecord.resource == "read", OperationalRecord.title == title))
    if not exists:
        session.add(OperationalRecord(tenant_id=account.tenant_id, entity="notification", resource="read", title=title, description="Notification read marker", status="READ"))

@router.patch("/notifications/read-all")
async def mark_all_notifications_read(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    account = await require_account(request, session)
    for row in await notifications(request, session):
        await mark_notification(session, account, row["id"])
    await session.commit()
    return {"ok": True}

@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    account = await require_account(request, session)
    await mark_notification(session, account, notification_id)
    await session.commit()
    return {"ok": True}
@router.patch("/notifications/{notification_id}/acknowledge")
async def acknowledge_notification(notification_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_account(request, session)
    try:
        parsed_id = uuid.UUID(notification_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Notification not found") from error
    memberships = await active_staff_memberships(session, account) if account.role != "patient" else []
    filters = [
        Notification.recipient_user_id == account.id,
        Notification.recipient_account_id == account.id,
    ]
    if memberships:
        filters.append(Notification.recipient_membership_id.in_([membership.id for membership in memberships]))
    notification = await session.scalar(
        select(Notification).where(Notification.id == parsed_id, or_(*filters)).with_for_update()
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

DOCTOR_RECORD_SECTIONS = {"identity", "triage", "allergies", "current_medications", "existing_conditions", "diagnoses", "appointments", "clinical_notes", "laboratory_results", "imaging_results", "prescriptions", "care_plans", "referrals", "hmo", "emergency_contact"}
NURSE_RECORD_SECTIONS = {"identity", "triage", "allergies", "current_medications", "appointments", "care_plans", "safety_warnings"}


async def record_access_audit(session: AsyncSession, request: Request, account: AuthAccount, membership: StaffMembership | None, ticket: Ticket, *, outcome: str, sections: set[str], reason: str, appointment_id: uuid.UUID | None = None, break_glass: bool = False) -> None:
    patient = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
    await write_audit_log(
        session,
        AuditAction.PATIENT_RECORD_VIEWED,
        actor_id=str(account.id),
        actor_type=account.role.upper(),
        tenant_id=str(ticket_destination_id(ticket)),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="PatientRecord",
        resource_id=str(ticket.id),
        user_agent=request.headers.get("user-agent"),
        metadata={"outcome": outcome, "membership_id": str(membership.id) if membership else None, "patient_id": str(patient.id) if patient else None, "hospital_id": str(ticket_destination_id(ticket)), "appointment_id": str(appointment_id) if appointment_id else None, "access_reason": reason, "record_sections_viewed": sorted(sections), "session_id": request.cookies.get(ACCESS_COOKIE, "")[-12:] or None, "break_glass_used": break_glass},
    )


async def clinician_record_context(session: AsyncSession, request: Request, ticket_id: uuid.UUID) -> tuple[AuthAccount, StaffMembership, Ticket, Appointment | None, CareTeamAssignment | None, bool]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse"})
    memberships = await active_staff_memberships(session, account)
    ticket = None
    membership = None
    for candidate in memberships:
        await apply_tenant_context(session, candidate.hospital_id)
        candidate_ticket = await session.scalar(select(Ticket).where(Ticket.id == ticket_id, ticket_visible_to_tenant(candidate.hospital_id)))
        if candidate_ticket and ticket_destination_id(candidate_ticket) == candidate.hospital_id:
            ticket, membership = candidate_ticket, candidate
            break
    if not ticket or not membership:
        await write_audit_log(session, AuditAction.PATIENT_RECORD_VIEWED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(account.tenant_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="PatientRecord", resource_id=str(ticket_id), user_agent=request.headers.get("user-agent"), metadata={"outcome": "DENIED", "access_reason": "NO_ACTIVE_TREATMENT_WORKSPACE", "record_sections_viewed": [], "break_glass_used": False})
        await session.commit()
        raise HTTPException(status_code=404, detail="Patient record not found in an active treatment workspace")
    hospital_id = ticket_destination_id(ticket)
    if not membership:
        await record_access_audit(session, request, account, None, ticket, outcome="DENIED", sections=set(), reason="NO_ACTIVE_MEMBERSHIP")
        await session.commit()
        raise HTTPException(status_code=403, detail="No active verified membership at the routed hospital")
    appointment = await session.scalar(select(Appointment).where(Appointment.ticket_id == ticket.id, Appointment.hospital_id == hospital_id, Appointment.department_id == membership.department_id, Appointment.doctor_id == account.id, Appointment.staff_membership_id == membership.id, Appointment.status == "BOOKED").order_by(Appointment.created_at.desc()).limit(1))
    care_assignment = await session.scalar(select(CareTeamAssignment).where(CareTeamAssignment.ticket_id == ticket.id, CareTeamAssignment.hospital_id == hospital_id, CareTeamAssignment.department_id == membership.department_id, CareTeamAssignment.user_id == account.id, CareTeamAssignment.membership_id == membership.id, CareTeamAssignment.status == "ACTIVE", CareTeamAssignment.starts_at <= utc_now(), or_(CareTeamAssignment.ends_at.is_(None), CareTeamAssignment.ends_at >= utc_now())).limit(1))
    if ticket.queue_status == "RESOLVED":
        appointment = None
        care_assignment = None
    directly_assigned = account.role in {"doctor", "specialist"} and ticket.assigned_specialist_id == account.id and ticket.queue_status != "RESOLVED" and membership.department_id == department_for_specialty(ticket.assigned_specialty) and membership.specialty_id == ticket.assigned_specialty
    grant = await session.scalar(select(BreakGlassGrant).where(BreakGlassGrant.ticket_id == ticket.id, BreakGlassGrant.user_id == account.id, BreakGlassGrant.membership_id == membership.id, BreakGlassGrant.confirmed.is_(True), BreakGlassGrant.revoked_at.is_(None), BreakGlassGrant.expires_at > utc_now()).order_by(BreakGlassGrant.created_at.desc()).limit(1))
    patient_account = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
    if patient_account:
        patient_registry = await ensure_patient_registry(session, patient_account)
        consent = await session.scalar(select(PatientConsentDirective).where(PatientConsentDirective.patient_id == patient_registry.id, PatientConsentDirective.purpose == "CARE_DELIVERY", PatientConsentDirective.status == "ACTIVE").limit(1))
        if not consent and not grant:
            await record_access_audit(session, request, account, membership, ticket, outcome="DENIED", sections=set(), reason="PATIENT_CONSENT_WITHDRAWN")
            await session.commit()
            raise HTTPException(status_code=403, detail="Patient consent does not permit record access")
    if account.role == "nurse" and not care_assignment and not grant:
        await record_access_audit(session, request, account, membership, ticket, outcome="DENIED", sections=set(), reason="NO_ASSIGNED_NURSING_DUTY")
        await session.commit()
        raise HTTPException(status_code=403, detail="An assigned nursing task or care-team responsibility is required")
    if account.role in {"doctor", "specialist"} and not appointment and not care_assignment and not directly_assigned and not grant:
        await record_access_audit(session, request, account, membership, ticket, outcome="DENIED", sections=set(), reason="NO_ACTIVE_TREATMENT_RELATIONSHIP")
        await session.commit()
        raise HTTPException(status_code=403, detail="No active treatment relationship for this patient")
    return account, membership, ticket, appointment, care_assignment, bool(grant)


@router.get("/clinician/patients/{ticket_id}/record")
async def clinician_patient_record(ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, membership, ticket, appointment, care_assignment, break_glass = await clinician_record_context(session, request, ticket_id)
    role_sections = NURSE_RECORD_SECTIONS if account.role == "nurse" else DOCTOR_RECORD_SECTIONS
    assignment_sections = set(json.loads(care_assignment.permitted_sections_json)) if care_assignment and care_assignment.permitted_sections_json else role_sections
    permitted = role_sections & assignment_sections if care_assignment else role_sections
    requested_param = str(request.query_params.get("sections") or "").strip()
    requested = {item.strip() for item in requested_param.split(",") if item.strip()} if requested_param else permitted
    if not requested <= permitted:
        await record_access_audit(session, request, account, membership, ticket, outcome="DENIED", sections=requested, reason="SECTION_NOT_PERMITTED", appointment_id=appointment.id if appointment else None, break_glass=break_glass)
        await session.commit()
        raise HTTPException(status_code=403, detail="One or more requested record sections are not permitted")
    patient = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
    notes = list((await session.execute(select(ConsultationNote).where(ConsultationNote.ticket_id == ticket.id).order_by(ConsultationNote.created_at.desc()))).scalars().all()) if "clinical_notes" in requested else []
    appointments = list((await session.execute(select(Appointment).where(Appointment.ticket_id == ticket.id).order_by(Appointment.created_at.desc()))).scalars().all()) if "appointments" in requested else []
    values: dict[str, Any] = {
        "identity": {"id": str(patient.id) if patient else None, "first_name": patient.first_name if patient else None, "last_name": patient.last_name if patient else None, "card_number": patient.card_number if patient else None},
        "triage": {"ticket_id": str(ticket.id), "symptoms": ticket.raw_intake_text, "condition": ticket.matched_condition_id, "urgency": ticket.urgency_level, "specialty": ticket.assigned_specialty},
        "allergies": patient.known_allergies if patient else None,
        "current_medications": patient.current_medications if patient else None,
        "existing_conditions": [], "diagnoses": [], "laboratory_results": [], "imaging_results": [], "prescriptions": [], "care_plans": [], "referrals": [], "safety_warnings": [],
        "appointments": [{"id": str(item.id), "status": item.status, "starts_at": item.starts_at, "department_id": item.department_id, "specialty_id": item.specialty_id} for item in appointments],
        "clinical_notes": [{"id": str(note.id), "body": note.body, "created_at": note.created_at} for note in notes],
        "hmo": {"provider": patient.hmo_provider if patient else None},
        "emergency_contact": patient.emergency_contact if patient else None,
    }
    await record_access_audit(session, request, account, membership, ticket, outcome="ALLOWED", sections=requested, reason="BREAK_GLASS" if break_glass else "ACTIVE_TREATMENT", appointment_id=appointment.id if appointment else None, break_glass=break_glass)
    await session.commit()
    return {"patient_id": str(patient.id) if patient else None, "ticket_id": str(ticket.id), "hospital_id": str(ticket_destination_id(ticket)), "department_id": membership.department_id, "relationship": "BREAK_GLASS" if break_glass else "ACTIVE_TREATMENT", "sections": {section: values[section] for section in sorted(requested)}}


@router.post("/clinician/patients/{ticket_id}/break-glass", status_code=201)
async def create_break_glass_access(ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse"})
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 10 or payload.get("confirmed") is not True:
        raise HTTPException(status_code=422, detail="A specific emergency reason and explicit confirmation are required")
    ticket = None
    membership = None
    for candidate in await active_staff_memberships(session, account):
        await apply_tenant_context(session, candidate.hospital_id)
        candidate_ticket = await session.scalar(select(Ticket).where(Ticket.id == ticket_id, ticket_visible_to_tenant(candidate.hospital_id)))
        if candidate_ticket and ticket_destination_id(candidate_ticket) == candidate.hospital_id:
            ticket, membership = candidate_ticket, candidate
            break
    if not ticket or not membership:
        await write_audit_log(session, AuditAction.PATIENT_RECORD_VIEWED, actor_id=str(account.id), actor_type=account.role.upper(), tenant_id=str(account.tenant_id), ip_address=request.client.host if request.client else "127.0.0.1", resource_type="PatientRecord", resource_id=str(ticket_id), metadata={"outcome": "DENIED", "access_reason": "BREAK_GLASS_NO_ACTIVE_MEMBERSHIP", "record_sections_viewed": [], "break_glass_used": True})
        await session.commit()
        raise HTTPException(status_code=403, detail="Break-glass requires active membership at the routed hospital")
    hospital_id = ticket_destination_id(ticket)
    if not membership:
        await record_access_audit(session, request, account, None, ticket, outcome="DENIED", sections=set(), reason="BREAK_GLASS_NO_ACTIVE_MEMBERSHIP", break_glass=True)
        await session.commit()
        raise HTTPException(status_code=403, detail="Break-glass requires active membership at the routed hospital")
    grant = BreakGlassGrant(hospital_id=hospital_id, ticket_id=ticket.id, user_id=account.id, membership_id=membership.id, reason=reason, confirmed=True, expires_at=utc_now() + timedelta(minutes=30))
    session.add(grant)
    await session.flush()
    await record_access_audit(session, request, account, membership, ticket, outcome="ALLOWED", sections=set(), reason=reason, break_glass=True)
    compliance_rows = (await session.execute(select(AuthAccount, StaffMembership).join(StaffMembership, StaffMembership.user_id == AuthAccount.id).where(StaffMembership.hospital_id == hospital_id, StaffMembership.role.in_(["hospital_admin", "department_coordinator"]), StaffMembership.is_active.is_(True), StaffMembership.verification_status == "VERIFIED", StaffMembership.employment_status == "ACTIVE"))).all()
    for recipient, recipient_membership in compliance_rows:
        await create_appointment_notification(session, tenant_id=hospital_id, recipient_account_id=recipient.id, recipient_role=recipient_membership.role, appointment=None, ticket=ticket, event_type="BREAK_GLASS_REVIEW_REQUIRED", title="Emergency patient-record access", body="A clinician used emergency access. Compliance review is required.", payload={"grant_id": str(grant.id), "ticket_id": str(ticket.id), "clinician_id": str(account.id)}, recipient_membership_id=recipient_membership.id, hospital_id=hospital_id, department_id=membership.department_id, priority="HIGH")
    patient = await session.scalar(select(AuthAccount).where(AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone))
    if patient:
        await create_appointment_notification(session, tenant_id=ticket.tenant_id, recipient_account_id=patient.id, recipient_role="patient", appointment=None, ticket=ticket, event_type="PATIENT_RECORD_EMERGENCY_ACCESS", title="Emergency record access", body="Your record was accessed for immediate emergency care.", payload={"ticket_id": str(ticket.id), "grant_id": str(grant.id)}, priority="HIGH")
    await session.commit()
    return {"id": str(grant.id), "status": "ACTIVE", "expires_at": grant.expires_at, "review_required": True}

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

async def require_specialist_workspace(request: Request, session: AsyncSession) -> tuple[AuthAccount, StaffMembership]:
    account = await require_specialist(request, session)
    membership = await require_staff_workspace(session, account, roles={"doctor", "specialist"})
    return account, membership

@router.get("/specialist/{resource}")
async def specialist_resource(resource: str, request: Request, assigned_only: bool = False, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    if resource not in SPECIALIST_RESOURCES:
        raise HTTPException(status_code=404, detail="Specialist resource not found")
    account, membership = await require_specialist_workspace(request, session)
    hospital_id = membership.hospital_id
    ticket_query = select(Ticket).where(ticket_destination_queue(hospital_id), Ticket.assigned_specialist_id == account.id)
    if assigned_only:
        ticket_query = ticket_query.where(Ticket.assigned_specialist_id == account.id)
    tickets = list((await session.execute(ticket_query.order_by(Ticket.created_at.desc()))).scalars().all())
    providers = list((await session.execute(
        select(Provider).where(Provider.tenant_id == hospital_id, Provider.doctor_id == account.id)
    )).scalars().all())
    provider_ids = [provider.id for provider in providers]
    appointment_rows = list((await session.execute(
        select(Appointment, ProviderSlot, Provider)
        .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id).join(Provider, Provider.id == ProviderSlot.provider_id)
        .where(Appointment.hospital_id == hospital_id, Appointment.doctor_id == account.id, Appointment.staff_membership_id == membership.id, ProviderSlot.provider_id.in_(provider_ids or [uuid.uuid4()]))
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
        notes = list((await session.execute(select(ConsultationNote).where(ConsultationNote.tenant_id == hospital_id, ConsultationNote.specialist_id == account.id).order_by(ConsultationNote.updated_at.desc()))).scalars().all())
        return {"identity": identity, "items": [{"id": str(note.id), "title": f"Ticket {note.ticket_id}", "body": note.body, "updated_at": note.updated_at.isoformat(), "status": "SIGNED"} for note in notes]}
    if resource == "messages":
        messages = list((await session.execute(select(SpecialistMessage).where(SpecialistMessage.tenant_id == hospital_id, SpecialistMessage.specialist_id == account.id).order_by(SpecialistMessage.created_at.desc()))).scalars().all())
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
    account, membership = await require_specialist_workspace(request, session)
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), ticket_destination_queue(membership.hospital_id)).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    expected_department = department_for_specialty(ticket.assigned_specialty)
    if membership.department_id != expected_department or (ticket.assigned_specialty and membership.specialty_id != ticket.assigned_specialty):
        raise HTTPException(status_code=403, detail="Ticket requires a matching department and specialty membership")
    if ticket.assigned_specialist_id not in {None, account.id}:
        raise HTTPException(status_code=409, detail="Ticket is assigned to another specialist")
    ticket.assigned_specialist_id = account.id
    await session.commit()
    return build_ticket_response(ticket)


@router.patch("/specialist/patients/{ticket_id}/status")
async def specialist_patient_status(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    payload = await request.json()
    account, membership = await require_specialist_workspace(request, session)
    status = payload.get("queue_status")
    if status not in {"QUEUED", "BEING_SEEN", "RESOLVED"}:
        raise HTTPException(status_code=422, detail="Invalid queue status")
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), ticket_destination_queue(membership.hospital_id)).with_for_update())
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
    account, membership = await require_specialist_workspace(request, session)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 3:
        raise HTTPException(status_code=422, detail="Consultation note is required")
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), ticket_destination_queue(membership.hospital_id), Ticket.assigned_specialist_id == account.id))
    if not ticket:
        raise HTTPException(status_code=404, detail="Assigned ticket not found")
    note = ConsultationNote(tenant_id=membership.hospital_id, ticket_id=ticket.id, specialist_id=account.id, body=body)
    session.add(note)
    await session.commit()
    return {"id": str(note.id), "ticket_id": str(ticket.id), "body": note.body, "created_at": note.created_at}


@router.post("/specialist/messages", status_code=201)
async def create_specialist_message(request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, membership = await require_specialist_workspace(request, session)
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 2:
        raise HTTPException(status_code=422, detail="Message body is required")
    message = SpecialistMessage(tenant_id=membership.hospital_id, specialist_id=account.id, sender_label=str(payload.get("sender_label") or "Specialist"), body=body, is_read=True)
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
    if entity != "admin" or resource not in OPERATIONAL_RESOURCES:
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
    if entity != "admin" or resource not in OPERATIONAL_RESOURCES:
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




FACILITY_DECISION_STATES = {
    "ACCEPT": "ACCEPTED",
    "REJECT": "REJECTED",
    "REDIRECT": "REDIRECTED",
}
QUEUE_TRANSITIONS = {
    "ACCEPTED": {"TRAVELLING", "ARRIVED", "CANCELLED"},
    "REJECTED": {"AWAITING_CLINICAL_REVIEW"},
    "REDIRECTED": {"AWAITING_FACILITY_ACCEPTANCE"},
    "TRAVELLING": {"ARRIVED", "CANCELLED"},
    "ARRIVED": {"CHECKED_IN", "CANCELLED"},
    "CHECKED_IN": {"WAITING_FOR_NURSE", "WAITING_FOR_DOCTOR", "CANCELLED"},
    "WAITING_FOR_NURSE": {"WAITING_FOR_DOCTOR", "BEING_SEEN", "CANCELLED"},
    "WAITING_FOR_DOCTOR": {"BEING_SEEN", "CANCELLED"},
    "BEING_SEEN": {"ADMITTED", "DISCHARGED", "TRANSFERRED", "RESOLVED"},
    "ADMITTED": {"DISCHARGED", "TRANSFERRED"},
}

@router.post("/hospital/tickets/{ticket_id}/facility-decision", status_code=201)
async def facility_ticket_decision(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    account, membership, _ = await require_hospital_membership(request, session, {"hospital_admin", "admin"})
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    reason = str(payload.get("reason") or "").strip()
    if decision not in FACILITY_DECISION_STATES:
        raise HTTPException(status_code=422, detail="Decision must be ACCEPT, REJECT, or REDIRECT")
    if decision in {"REJECT", "REDIRECT"} and len(reason) < 10:
        raise HTTPException(status_code=422, detail="A clear reason is required for rejection or redirection")
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), Ticket.routed_tenant_id == membership.hospital_id).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Routed ticket not found")
    if ticket.queue_status not in {"QUEUED", "ROUTED", "AWAITING_FACILITY_ACCEPTANCE"}:
        raise HTTPException(status_code=409, detail="Ticket can no longer receive a facility decision")
    redirected_id = None
    if decision == "REDIRECT":
        try:
            redirected_id = uuid.UUID(str(payload.get("redirect_facility_id")))
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail="A valid redirect facility is required") from error
        destination = await session.get(Tenant, redirected_id)
        destination_registry = await session.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == redirected_id))
        if not destination or destination.status != "ACTIVE" or destination.id == membership.hospital_id or not destination_registry or destination_registry.status != "ACTIVE" or not destination_registry.accepts_patients:
            raise HTTPException(status_code=422, detail="Redirect facility must be a different active registered facility that accepts patients")
    previous = ticket.queue_status
    next_status = FACILITY_DECISION_STATES[decision]
    ticket.queue_status = "AWAITING_FACILITY_ACCEPTANCE" if decision == "REDIRECT" else next_status
    if decision == "REDIRECT" and redirected_id:
        ticket.routed_tenant_id = redirected_id
    ticket.version += 1
    session.add(FacilityAcceptance(ticket_id=ticket.id, facility_id=membership.hospital_id, actor_account_id=account.id, actor_membership_id=membership.id, decision=decision, previous_status=previous, next_status=next_status, reason=reason or None, redirected_facility_id=redirected_id))
    session.add(OutboxEvent(tenant_id=membership.hospital_id, aggregate_type="Ticket", aggregate_id=ticket.id, event_type=f"facility.{decision.lower()}", payload_json=json.dumps({"ticket_id": str(ticket.id), "decision": decision, "redirected_facility_id": str(redirected_id) if redirected_id else None}), classification="RESTRICTED", status="PENDING"))
    await session.commit()
    return {"ticket": build_ticket_response(ticket), "decision": decision, "reason": reason or None, "redirected_facility_id": redirected_id}

@router.post("/hospital/tickets/{ticket_id}/transition")
async def transition_facility_ticket(ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)) -> TicketResponse:
    account, membership, _ = await require_hospital_membership(request, session)
    payload = await request.json()
    next_status = str(payload.get("status") or "").upper()
    ticket = await session.scalar(select(Ticket).where(Ticket.id == uuid.UUID(ticket_id), Ticket.routed_tenant_id == membership.hospital_id).with_for_update())
    if not ticket:
        raise HTTPException(status_code=404, detail="Routed ticket not found")
    if next_status not in QUEUE_TRANSITIONS.get(ticket.queue_status, set()):
        raise HTTPException(status_code=409, detail=f"Invalid transition from {ticket.queue_status} to {next_status}")
    previous = ticket.queue_status
    ticket.queue_status = next_status
    ticket.version += 1
    session.add(FacilityAcceptance(ticket_id=ticket.id, facility_id=membership.hospital_id, actor_account_id=account.id, actor_membership_id=membership.id, decision="TRANSITION", previous_status=previous, next_status=next_status, reason=str(payload.get("reason") or "").strip() or None))
    event_type = "patient.checked_in" if next_status == "CHECKED_IN" else "patient.status_changed"
    session.add(OutboxEvent(tenant_id=membership.hospital_id, aggregate_type="Ticket", aggregate_id=ticket.id, event_type=event_type, payload_json=json.dumps({"ticket_id": str(ticket.id), "previous_status": previous, "status": next_status}), classification="RESTRICTED", status="PENDING"))
    await session.commit()
    return build_ticket_response(ticket)
