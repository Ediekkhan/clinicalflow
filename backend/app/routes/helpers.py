from __future__ import annotations

import json
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any

from collections import defaultdict

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    Appointment,
    ApplicationReviewHistory,
    AppointmentAssignmentRequest,
    AuthAccount,
    AuthSession,
    AuditLog,
    BillingCustomer,
    BreakGlassGrant,
    CareTeamAssignment,
    CheckoutSession,
    ClinicalPrivilege,
    ClientMutation,
    ConsentRecord,
    ConsultationNote,
    DemoRequest,
    EnterpriseEnquiry,
    ExternalRegistryCheck,
    FacilityAcceptance,
    FacilityAdminActivation,
    FacilityRegistry,
    FacilityService,
    FacilityVerificationCase,
    HealthCardCredential,
    HospitalDepartment,
    HospitalDoctorMembership,
    Invoice,
    LaboratoryOrder,
    DiagnosticReport,
    Notification,
    NotificationDelivery,
    OperationalRecord,
    OrganizationApplication,
    OrganizationOnboardingDraft,
    OutboxEvent,
    PatientConsentDirective,
    PatientFacilityIdentity,
    PatientRegistry,
    PaymentAttempt,
    PaymentWebhookEvent,
    ProfessionalCredential,
    ProvenanceRecord,
    Provider,
    ProviderAvailability,
    ProviderRegistry,
    ProviderSlot,
    ReconciliationIssue,
    RefundRecord,
    RoutingCandidate,
    RoutingDecision,
    SignupApplication,
    SpecialistMessage,
    Specialty,
    StaffInvitation,
    StaffMembership,
    Subscription,
    TerminologyRelease,
    Ticket,
    Tenant,
    VerificationDocument,
    VerificationEvent,
    VerificationFinding,
)
from app.schemas import (
    AppointmentCreate,
    AppointmentMoveRequest,
    AppointmentResponse,
    AuthLoginRequest,
    AuthProfileResponse,
    AuthRefreshResponse,
    AuthSessionResponse,
    ChannelIntakeRequest,
    ChannelIntakeResponse,
    ChannelMenuOption,
    DemoRequestCreate,
    DemoRequestResponse,
    EnterpriseEnquiryCreate,
    EnterpriseEnquiryUpdate,
    HospitalLoginRequest,
    PatientCardUpdate,
    PatientProfileUpdate,
    PinLoginRequest,
    RefundCreate,
    ReconciliationResolve,
    SignupApplicationCreate,
    SignupApplicationResponse,
    SignupInvitationValidateRequest,
    SignupVerificationRequest,
    SlotLockRequest,
    TicketCreate,
    TicketResponse,
    TicketUpdate,
    SlotResponse,
)
from app.services.audit_service import AuditAction, write_audit_log
from app.services.auth_service import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    account_for_access_token,
    apply_tenant_context,
    create_session,
    find_account,
    hash_password,
    session_for_refresh_token,
    token_hash,
    utc_now,
    verify_password,
)
from app.services.channel_service import (
    SMS_TEMPLATES,
    intent_from_text,
    normalize_webhook,
    valid_signature,
)
from app.services.facility_routing import (
    rank_eligible_facilities,
    select_nearest_eligible_hospital,
    valid_coordinates,
)
from app.services.registry_service import (
    ensure_facility_registry,
    ensure_patient_registry,
    ensure_provider_registry,
    issue_health_card_credential,
    patient_duplicate_key,
)
from app.services.supabase_auth import password_login, provision_user, SupabaseAuthError
from app.services.facility_verification import review_due_at
from app.services.country_policies import country_policy, radius_for_urgency
from app.services.payment_providers import (
    PaymentProviderError,
    provider_for_country,
    provider_for_name,
)
from app.services.storage_service import (
    delete_object,
    object_metadata,
    private_object_key,
    signed_download_url,
    signed_upload_url,
    validate_document,
    StorageNotConfigured,
)


KNOWN_SYMPTOM_TERMS = (
    "bleeding",
    "breathing",
    "chest pain",
    "cough",
    "dizziness",
    "fever",
    "headache",
    "nausea",
    "pain",
    "rash",
    "vomiting",
    "weakness",
)


def extract_symptom_terms(intake_text: str) -> str | None:
    normalized = intake_text.casefold()
    matches = [term for term in KNOWN_SYMPTOM_TERMS if term in normalized]
    return json.dumps(matches) if matches else None


def severity_for_urgency(urgency: str) -> str:
    return {"CRITICAL": "SEVERE", "URGENT": "MODERATE", "ROUTINE": "MILD"}.get(
        urgency, "MILD"
    )


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
        if "fever" in symptom_set and (
            "vomiting" in symptom_set or "weakness" in symptom_set
        ):
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
        raise HTTPException(
            status_code=422,
            detail="Patient latitude and longitude must be valid numbers",
        )


def patient_coordinates_from_payload(payload: dict[str, Any]) -> tuple[float, float]:
    latitude = coordinate_value(payload, "latitude")
    longitude = coordinate_value(payload, "longitude")
    if latitude is None or longitude is None:
        raise HTTPException(
            status_code=422,
            detail="Patient location is required to route this ticket to the nearest registered hospital",
        )
    if not valid_coordinates(latitude, longitude):
        raise HTTPException(
            status_code=422,
            detail="Patient coordinates are outside the valid latitude/longitude range",
        )
    return latitude, longitude


def ticket_visible_to_tenant(tenant_id: uuid.UUID):
    return or_(Ticket.tenant_id == tenant_id, Ticket.routed_tenant_id == tenant_id)


def ticket_destination_queue(tenant_id: uuid.UUID):
    return or_(
        Ticket.routed_tenant_id == tenant_id,
        (Ticket.routed_tenant_id.is_(None) & (Ticket.tenant_id == tenant_id)),
    )


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


async def active_staff_memberships(
    session: AsyncSession, account: AuthAccount
) -> list[StaffMembership]:
    now = utc_now()
    return list(
        (
            await session.execute(
                select(StaffMembership).where(
                    StaffMembership.user_id == account.id,
                    StaffMembership.is_active.is_(True),
                    StaffMembership.verification_status == "VERIFIED",
                    StaffMembership.employment_status == "ACTIVE",
                    StaffMembership.active_from <= now,
                    or_(
                        StaffMembership.active_until.is_(None),
                        StaffMembership.active_until >= now,
                    ),
                )
            )
        )
        .scalars()
        .all()
    )


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
        or_(
            StaffMembership.active_until.is_(None), StaffMembership.active_until >= now
        ),
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
        query = query.where(
            StaffMembership.id == uuid.UUID(str(selected_membership_id))
        )
    else:
        memberships = await active_staff_memberships(session, account)
        if len(memberships) > 1:
            if (
                account.identifier.startswith("uyo-family:")
                or account.identifier == "dr.ada@example.com"
            ):
                query = query.where(StaffMembership.hospital_id == account.tenant_id)
            else:
                raise HTTPException(
                    status_code=409,
                    detail="Select an active staff workspace before continuing",
                )
    membership = await session.scalar(
        query.order_by(StaffMembership.created_at.asc()).limit(1)
    )
    if not membership:
        raise HTTPException(
            status_code=403,
            detail="No verified active staff membership for this workspace",
        )
    if privileges:
        granted = set(
            (
                await session.execute(
                    select(ClinicalPrivilege.code).where(
                        ClinicalPrivilege.membership_id == membership.id,
                        ClinicalPrivilege.code.in_(sorted(privileges)),
                        ClinicalPrivilege.status == "ACTIVE",
                        ClinicalPrivilege.revoked_at.is_(None),
                        or_(
                            ClinicalPrivilege.expires_at.is_(None),
                            ClinicalPrivilege.expires_at >= now,
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        missing = privileges - granted
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing clinical privilege: {sorted(missing)[0]}",
            )
    await apply_tenant_context(session, membership.hospital_id)
    return membership


def build_ticket_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        tenant_id=ticket.tenant_id,
        ticket_number=ticket.ticket_number,
        customer_phone=ticket.customer_phone,
        account_group_phone=ticket.account_group_phone,
        channel=ticket.channel,
        urgency_level=ticket.urgency_level,
        matched_condition_id=ticket.matched_condition_id,
        assigned_specialty=ticket.assigned_specialty,
        queue_status=ticket.queue_status,
        is_manually_escalated=ticket.is_manually_escalated,
        appointment_slot=ticket.appointment_slot,
        patient_latitude=ticket.patient_latitude,
        patient_longitude=ticket.patient_longitude,
        routed_tenant_id=ticket.routed_tenant_id,
        route_distance_km=ticket.route_distance_km,
        created_at=ticket.created_at,
        raw_intake_text=ticket.raw_intake_text,
        extracted_symptoms=ticket.extracted_symptoms,
        version=ticket.version,
    )


async def replayed_mutation(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    key: str | None,
    action: str,
    resource_id: uuid.UUID,
) -> TicketResponse | None:
    if not key:
        return None
    if len(key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency key is too long")
    receipt = await session.scalar(
        select(ClientMutation).where(
            ClientMutation.tenant_id == tenant_id, ClientMutation.idempotency_key == key
        )
    )
    if not receipt:
        return None
    if receipt.action != action or receipt.resource_id != resource_id:
        raise HTTPException(
            status_code=409,
            detail="Idempotency key was already used for another mutation",
        )
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
        sockets = (
            self._account_connections.get(str(target_account_id), set())
            if target_account_id
            else self._connections.get(tenant_id, set())
        )
        for websocket in list(sockets):
            try:
                await websocket.send_json(event)
            except Exception:
                dead_sockets.append(websocket)
        for websocket in dead_sockets:
            self.disconnect(tenant_id, websocket)


triage_manager = TriageConnectionManager()


async def broadcast_ticket_event(
    ticket: Ticket, event_type: str, payload: dict[str, Any], priority: str = "NORMAL"
) -> None:
    tenant_ids = {
        str(ticket.tenant_id),
        str(ticket.routed_tenant_id or ticket.tenant_id),
    }
    for tenant_id in tenant_ids:
        await triage_manager.broadcast(
            tenant_id,
            {
                "type": event_type,
                "tenant_id": tenant_id,
                "payload": payload,
                "priority": priority,
            },
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
        hospital_id=hospital_id
        or (appointment.hospital_id if appointment else tenant_id),
        department_id=department_id
        or (appointment.department_id if appointment else None),
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
    session.add(
        OutboxEvent(
            tenant_id=tenant_id,
            aggregate_type="Notification",
            aggregate_id=notification.id,
            event_type=event_type,
            recipient_user_id=recipient_account_id,
            payload_json=json.dumps(
                {
                    "notification_id": str(notification.id),
                    "appointment_id": str(appointment.id) if appointment else None,
                    "ticket_id": str(ticket.id),
                    "recipient_user_id": (
                        str(recipient_account_id) if recipient_account_id else None
                    ),
                },
                default=str,
            ),
            classification="RESTRICTED",
            status="PENDING",
        )
    )
    channels = {"REALTIME"}
    if recipient_membership_id:
        membership = await session.get(StaffMembership, recipient_membership_id)
        if membership and membership.notification_preferences:
            try:
                preferences = json.loads(membership.notification_preferences)
                if isinstance(preferences, dict):
                    channels.update(
                        str(channel).upper()
                        for channel, enabled in preferences.items()
                        if enabled
                        and str(channel).upper() in {"EMAIL", "SMS", "PUSH", "WHATSAPP"}
                    )
                elif isinstance(preferences, list):
                    channels.update(
                        str(channel).upper()
                        for channel in preferences
                        if str(channel).upper() in {"EMAIL", "SMS", "PUSH", "WHATSAPP"}
                    )
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
    session.add_all(
        [
            NotificationDelivery(
                notification_id=notification.id, channel=channel, status="PENDING"
            )
            for channel in sorted(channels)
        ]
    )
    return notification


async def broadcast_appointment_event(
    tenant_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any],
    recipient_account_id: uuid.UUID | None = None,
    *,
    session: AsyncSession | None = None,
    notification_id: uuid.UUID | None = None,
) -> None:
    delivery = (
        await session.scalar(
            select(NotificationDelivery)
            .where(
                NotificationDelivery.notification_id == notification_id,
                NotificationDelivery.channel == "REALTIME",
            )
            .with_for_update()
        )
        if session and notification_id
        else None
    )
    try:
        await triage_manager.broadcast(
            str(tenant_id),
            {
                "type": event_type,
                "tenant_id": str(tenant_id),
                "recipient_account_id": (
                    str(recipient_account_id) if recipient_account_id else None
                ),
                "payload": payload,
                "priority": "NORMAL",
            },
        )
        if delivery:
            delivery.status, delivery.delivered_at, delivery.attempts = (
                "DELIVERED",
                utc_now(),
                delivery.attempts + 1,
            )
    except Exception as error:
        if delivery:
            (
                delivery.status,
                delivery.last_error,
                delivery.next_attempt_at,
                delivery.attempts,
            ) = (
                "RETRY_PENDING",
                str(error)[:1000],
                utc_now() + timedelta(minutes=2),
                delivery.attempts + 1,
            )
    if delivery and session:
        await session.commit()


async def enforce_rate_limit(
    request: Request, scope: str, limit: int, identity: str | None = None
) -> None:
    client_identity = identity or (request.client.host if request.client else "unknown")
    if not await request.app.state.redis.allow(scope, client_identity, limit):
        raise HTTPException(
            status_code=429,
            detail="Too many requests; please try again shortly",
            headers={"Retry-After": "60"},
        )


def _build_profile(account: AuthAccount) -> AuthProfileResponse:
    title = "Dr. " if account.role == "specialist" else ""
    return AuthProfileResponse(
        id=str(account.id),
        role=account.role,
        tenant_id=str(account.tenant_id),
        phone=account.phone,
        email=account.email,
        first_name=account.first_name,
        last_name=account.last_name,
        country_code=account.country_code,
        full_name=f"{title}{account.first_name} {account.last_name}",
        specialty=account.specialty,
        card_number=account.card_number,
        subtitle=f"{account.role.title()} portal",
        date_of_birth=account.date_of_birth,
        gender=account.gender,
        state=account.state,
        lga=account.lga,
        emergency_contact=account.emergency_contact,
        hmo_provider=account.hmo_provider,
        blood_group=account.blood_group,
        genotype=account.genotype,
        known_allergies=account.known_allergies,
        current_medications=account.current_medications,
        created_at=account.created_at,
        card_valid_from=account.created_at,
        card_valid_until=(
            account.created_at + timedelta(days=365 * 5)
            if account.card_number
            else None
        ),
        locked_fields=[],
    )


def _set_session_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    common = {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE, access_token, max_age=settings.auth_access_minutes * 60, **common
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.auth_refresh_days * 86400,
        **common,
    )


def _delete_legacy_auth_cookies(response: Response) -> None:
    for name in (
        "clinicalflow_access",
        "clinicalflow_refresh",
        "clinicalflow_role",
        "synaptiverse_session",
        "synaptiverse_access_token",
        "synaptiverse_refresh_token",
        "synaptiverse_csrf_token",
        "synaptiverse_auth",
        "demo_session",
        "demo_user",
        "demo_role",
    ):
        response.delete_cookie(name, path="/")


async def _login_account(
    account: AuthAccount, request: Request, response: Response, session: AsyncSession
) -> AuthSessionResponse:
    issued = await create_session(
        session,
        account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    memberships = list(
        (
            await session.execute(
                select(StaffMembership)
                .where(
                    StaffMembership.user_id == account.id,
                    StaffMembership.is_active.is_(True),
                    StaffMembership.employment_status == "ACTIVE",
                )
                .order_by(StaffMembership.active_from.desc())
            )
        )
        .scalars()
        .all()
    )
    if memberships and len({membership.hospital_id for membership in memberships}) == 1:
        issued.session.selected_membership_id = memberships[0].id
    await session.commit()
    _set_session_cookies(response, issued.access_token, issued.refresh_token)
    return AuthSessionResponse(
        **_build_profile(account).model_dump(),
        access_expires_at=issued.session.access_expires_at,
    )


async def get_db(request: Request) -> AsyncSession:
    session_factory: Any = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def require_account(request: Request, session: AsyncSession) -> AuthAccount:
    authorization = request.headers.get("authorization", "")
    token = request.cookies.get(ACCESS_COOKIE) or (
        authorization[7:].strip()
        if authorization.lower().startswith("bearer ")
        else None
    )
    authenticated = await account_for_access_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")
    account, auth_session = authenticated
    session.info["tenant_id"] = str(account.tenant_id)
    session.info["selected_membership_id"] = (
        str(auth_session.selected_membership_id)
        if auth_session and auth_session.selected_membership_id
        else None
    )
    if session.bind and session.bind.dialect.name == "postgresql":
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(account.tenant_id)},
        )
    return account


async def require_roles(
    request: Request, session: AsyncSession, allowed: set[str]
) -> AuthAccount:
    account = await require_account(request, session)
    if account.role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient role permissions")
    return account


def public_tenant_id() -> str:
    return settings.operational_tenant_id


async def tenant_control(
    session: AsyncSession, tenant_id: uuid.UUID, name: str, default: bool
) -> bool:
    record = await session.scalar(
        select(OperationalRecord).where(
            OperationalRecord.tenant_id == tenant_id,
            OperationalRecord.entity == "system",
            OperationalRecord.resource == "settings",
            OperationalRecord.title == name,
        )
    )
    return default if not record else record.status == "ENABLED"


async def require_hospital_membership(
    request: Request, session: AsyncSession, roles: set[str] | None = None
) -> tuple[AuthAccount, StaffMembership, Tenant | None]:
    account = await require_roles(
        request,
        session,
        {
            "doctor",
            "specialist",
            "nurse",
            "department_coordinator",
            "hospital_admin",
            "admin",
        },
    )
    membership = await require_staff_workspace(
        session,
        account,
        roles=roles
        or {
            "doctor",
            "specialist",
            "nurse",
            "department_coordinator",
            "hospital_admin",
        },
    )
    tenant = await session.get(Tenant, membership.hospital_id)
    return account, membership, tenant


def department_code(value: str) -> str:
    return value.strip().lower().replace(" ", "-") or "department"


async def resolve_hospital_department(
    session: AsyncSession, hospital_id: uuid.UUID, value: str
) -> HospitalDepartment | None:
    normalized = value.strip()
    department_uuid = None
    try:
        department_uuid = uuid.UUID(normalized)
    except (TypeError, ValueError):
        pass
    filters = (
        [HospitalDepartment.id == department_uuid]
        if department_uuid
        else [
            or_(
                HospitalDepartment.name == normalized,
                HospitalDepartment.code == normalized,
            )
        ]
    )
    return await session.scalar(
        select(HospitalDepartment).where(
            HospitalDepartment.hospital_id == hospital_id,
            HospitalDepartment.status == "ACTIVE",
            *filters,
        )
    )


async def hospital_ticket_items(
    session: AsyncSession, hospital_id: uuid.UUID
) -> list[dict[str, Any]]:
    rows = list(
        (
            await session.execute(
                select(Ticket, Appointment, AuthAccount, RoutingDecision)
                .outerjoin(RoutingDecision, RoutingDecision.ticket_id == Ticket.id)
                .outerjoin(Appointment, Appointment.ticket_id == Ticket.id)
                .outerjoin(AuthAccount, AuthAccount.id == Appointment.doctor_id)
                .where(ticket_destination_queue(hospital_id))
                .order_by(Ticket.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    items: list[dict[str, Any]] = []
    for ticket, appointment, doctor, routing_decision in rows:
        assignment_status = (
            "APPOINTMENT_CONFIRMED"
            if appointment and appointment.doctor_id
            else "AWAITING_ASSIGNMENT"
        )
        status = (
            "COMPLETED" if ticket.queue_status == "RESOLVED" else ticket.queue_status
        )
        if appointment and appointment.status == "CANCELLED":
            status = "CANCELLED"
        items.append(
            {
                "id": str(ticket.id),
                "patient_name": "Patient",
                "card_number": None,
                "ticket_number": ticket.ticket_number,
                "arrival_time": (
                    (appointment.starts_at or ticket.created_at).isoformat()
                    if appointment
                    else ticket.created_at.isoformat()
                ),
                "urgency": ticket.urgency_level,
                "required_specialty": ticket.assigned_specialty,
                "department": (
                    appointment.department_id
                    if appointment
                    else department_for_specialty(ticket.assigned_specialty)
                ),
                "assigned_doctor": (
                    f"{doctor.first_name} {doctor.last_name}"
                    if doctor
                    else "Awaiting assignment"
                ),
                "queue_status": ticket.queue_status,
                "status": status,
                "assignment_status": assignment_status,
                "routing_distance_km": ticket.route_distance_km,
                "routing_reason": (
                    routing_decision.selection_reason if routing_decision else None
                ),
                "routing_status": routing_decision.status if routing_decision else None,
                "acceptance_required": True,
                "appointment_status": appointment.status if appointment else None,
                "appointment_id": str(appointment.id) if appointment else None,
            }
        )
    return items


async def hospital_specialist_items(
    session: AsyncSession, hospital_id: uuid.UUID, department_id: str | None = None
) -> list[dict[str, Any]]:
    query = (
        select(AuthAccount, StaffMembership, Provider)
        .join(StaffMembership, StaffMembership.user_id == AuthAccount.id)
        .outerjoin(
            Provider,
            (Provider.doctor_id == AuthAccount.id)
            & (Provider.tenant_id == StaffMembership.hospital_id)
            & (Provider.specialty == StaffMembership.specialty_id),
        )
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
    rows = list(
        (
            await session.execute(
                query.order_by(StaffMembership.department_id, AuthAccount.last_name)
            )
        ).all()
    )
    items: list[dict[str, Any]] = []
    now = utc_now()
    for account, membership, provider in rows:
        booked_today = await session.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.hospital_id == hospital_id,
                Appointment.staff_membership_id == membership.id,
                Appointment.status == "BOOKED",
                Appointment.starts_at
                >= datetime.combine(now.date(), time.min, tzinfo=UTC),
                Appointment.starts_at
                < datetime.combine(now.date(), time.min, tzinfo=UTC)
                + timedelta(days=1),
            )
        )
        next_slot = None
        if provider:
            next_slot = await session.scalar(
                select(ProviderSlot)
                .where(
                    ProviderSlot.provider_id == provider.id,
                    ProviderSlot.tenant_id == hospital_id,
                    ProviderSlot.starts_at >= now,
                    ProviderSlot.is_locked.is_(False),
                    ProviderSlot.is_booked.is_(False),
                )
                .order_by(ProviderSlot.starts_at.asc())
                .limit(1)
            )
        capacity = membership.daily_capacity or (
            provider.max_daily_capacity if provider else 12
        )
        availability = "OFF_DUTY"
        if membership.is_on_duty:
            availability = (
                "FULLY_BOOKED" if (booked_today or 0) >= capacity else "AVAILABLE"
            )
        items.append(
            {
                "id": str(membership.id),
                "user_id": str(account.id),
                "full_name": f"{account.first_name} {account.last_name}",
                "title": account.role.replace("_", " ").title(),
                "specialty": membership.specialty_id,
                "department": membership.department_id,
                "license_status": membership.verification_status,
                "is_on_duty": membership.is_on_duty,
                "availability": availability,
                "next_available_slot": (
                    next_slot.starts_at.isoformat() if next_slot else None
                ),
                "appointments_today": booked_today or 0,
                "current_workload": booked_today or 0,
                "maximum_capacity": capacity,
                "room_label": provider.room_label if provider else None,
            }
        )
    return items


async def hospital_department_items(
    session: AsyncSession, hospital_id: uuid.UUID
) -> list[dict[str, Any]]:
    departments = list(
        (
            await session.execute(
                select(HospitalDepartment)
                .where(
                    HospitalDepartment.hospital_id == hospital_id,
                    HospitalDepartment.status == "ACTIVE",
                )
                .order_by(HospitalDepartment.name)
            )
        )
        .scalars()
        .all()
    )
    if not departments:
        names = sorted(
            {
                row[0]
                for row in (
                    await session.execute(
                        select(StaffMembership.department_id).where(
                            StaffMembership.hospital_id == hospital_id
                        )
                    )
                ).all()
                if row[0]
            }
        )
        departments = [
            HospitalDepartment(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"{hospital_id}:{name}"),
                hospital_id=hospital_id,
                name=name,
                code=department_code(name),
                status="ACTIVE",
            )
            for name in names
        ]
    items: list[dict[str, Any]] = []
    now = utc_now()
    for department in departments:
        doctors = await hospital_specialist_items(session, hospital_id, department.name)
        waiting = await session.scalar(
            select(func.count(Ticket.id)).where(
                ticket_destination_queue(hospital_id),
                Ticket.assigned_specialty == department.name,
                Ticket.queue_status == "QUEUED",
            )
        )
        appointments_today = await session.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.hospital_id == hospital_id,
                Appointment.department_id == department.name,
                Appointment.starts_at
                >= datetime.combine(now.date(), time.min, tzinfo=UTC),
                Appointment.starts_at
                < datetime.combine(now.date(), time.min, tzinfo=UTC)
                + timedelta(days=1),
            )
        )
        nurses_on_duty = await session.scalar(
            select(func.count(StaffMembership.id)).where(
                StaffMembership.hospital_id == hospital_id,
                StaffMembership.department_id == department.name,
                StaffMembership.role == "nurse",
                StaffMembership.is_on_duty.is_(True),
                StaffMembership.is_active.is_(True),
                StaffMembership.verification_status == "VERIFIED",
            )
        )
        items.append(
            {
                "id": str(department.id),
                "name": department.name,
                "code": department.code,
                "description": department.description,
                "status": department.status,
                "coordinator": None,
                "total_doctors": len(doctors),
                "available_doctors": sum(
                    doctor["availability"] == "AVAILABLE" for doctor in doctors
                ),
                "specialists_on_duty": sum(
                    bool(doctor["is_on_duty"]) for doctor in doctors
                ),
                "nurses_on_duty": nurses_on_duty or 0,
                "patients_waiting": waiting or 0,
                "appointments_today": appointments_today or 0,
                "average_wait_time_minutes": None,
                "capacity_status": (
                    "AVAILABLE"
                    if any(doctor["availability"] == "AVAILABLE" for doctor in doctors)
                    else "LIMITED"
                ),
                "available_doctors_list": doctors,
            }
        )
    return items


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
    routed_uuid = (
        routed_tenant_id if route_attempted else (routed_tenant_id or tenant_uuid)
    )
    tenant_id = str(tenant_uuid)
    await apply_tenant_context(session, tenant_uuid)
    ticket_number = (
        f"SV-{datetime.now(UTC).strftime('%Y-%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    )
    terminology_release_id = await session.scalar(
        select(TerminologyRelease.id)
        .where(TerminologyRelease.status == "PUBLISHED")
        .order_by(
            TerminologyRelease.release_date.desc(),
            TerminologyRelease.imported_at.desc(),
        )
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


SIGNUP_ONBOARDING_TYPES = {
    "patient": "PUBLIC_SELF_REGISTRATION",
    "specialist": "HOSPITAL_STAFF",
    "hospital": "ORGANIZATION_APPLICATION",
    "clinic": "ORGANIZATION_APPLICATION",
    "nurse": "HOSPITAL_STAFF",
    "pharmacy": "ORGANIZATION_APPLICATION",
    "laboratory": "ORGANIZATION_APPLICATION",
    "hmo": "ORGANIZATION_APPLICATION",
    "government": "INVITATION_ONLY",
    "platform-admin": "INVITATION_ONLY",
}
SIGNUP_PENDING_STATUSES = {
    "patient": "PHONE_VERIFICATION_REQUIRED",
    "specialist": "PENDING_HOSPITAL_APPROVAL",
    "hospital": "PENDING_FACILITY_VERIFICATION",
    "clinic": "PENDING_FACILITY_VERIFICATION",
    "nurse": "PENDING_HOSPITAL_APPROVAL",
    "pharmacy": "PENDING_PHARMACY_VERIFICATION",
    "laboratory": "PENDING_LABORATORY_VERIFICATION",
    "hmo": "PENDING_PAYER_VERIFICATION",
    "government": "PENDING_GOVERNMENT_VERIFICATION",
    "platform-admin": "PENDING_VERIFICATION",
}
SIGNUP_LOGIN_PATHS = {
    "patient": "/login",
    "specialist": "/specialist/login",
    "hospital": "/hospital/login",
    "clinic": "/auth/login",
    "nurse": "/auth/login",
    "pharmacy": "/auth/login",
    "laboratory": "/auth/login",
    "hmo": "/auth/login",
    "government": "/auth/login",
    "platform-admin": "/auth/login",
}
SIGNUP_DASHBOARD_PATHS = {
    "patient": "/dashboard",
    "specialist": "/specialist/dashboard",
    "hospital": "/hospital/dashboard",
    "clinic": "/clinic/dashboard",
    "nurse": "/nurse/dashboard",
    "pharmacy": "/pharmacy/dashboard",
    "laboratory": "/lab/dashboard",
    "hmo": "/hmo/dashboard",
    "government": "/moh/dashboard",
    "platform-admin": "/dashboard/admin",
}
ADMINISTRATOR_ROLES = {
    "SUPER_ADMIN",
    "SECURITY_ADMIN",
    "COMPLIANCE_ADMIN",
    "TENANT_REVIEWER",
    "SUPPORT_ADMIN",
    "AUDITOR",
}
FACILITY_VERIFIER_ROLES = {"facility_verifier", "verification_supervisor"}
INVITATION_ROLES = {
    "specialist": {"specialist", "doctor"},
    "nurse": {"nurse"},
    "government": {"government", "moh"},
    "platform-admin": {"platform-admin", "admin", *ADMINISTRATOR_ROLES},
}
ORGANIZATION_SIGNUP_TYPES = {
    "hospital",
    "clinic",
    "pharmacy",
    "laboratory",
    "hmo",
    "government",
}
PROFESSIONAL_SIGNUP_TYPES = {"specialist", "nurse"}


def _signup_value(payload: SignupApplicationCreate, key: str) -> Any:
    return payload.data.get(key, getattr(payload, key, None))


def _require_signup_fields(
    payload: SignupApplicationCreate, fields: tuple[str, ...]
) -> None:
    missing = [
        field.replace("_", " ")
        for field in fields
        if _signup_value(payload, field) in (None, "", [], False)
    ]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Required fields: {', '.join(missing)}"
        )


def _signup_reference() -> str:
    return f"SV-APP-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(4).upper()}"


def country_code_for_name(value: str | None) -> str:
    raw = str(value or "").strip().casefold()
    aliases = {
        "nigeria": "NG",
        "ghana": "GH",
        "kenya": "KE",
        "south africa": "ZA",
        "united kingdom": "GB",
        "united states": "US",
        "us": "US",
        "ng": "NG",
        "gb": "GB",
    }
    return aliases.get(raw, raw.upper() if len(raw) == 2 and raw.isalpha() else "")


async def _validated_invitation(
    session: AsyncSession, role: str, raw_token: str | None, email: str | None
) -> StaffInvitation | None:
    if not raw_token:
        return None
    invitation = await session.scalar(
        select(StaffInvitation).where(
            StaffInvitation.token_hash == token_hash(raw_token)
        )
    )
    now = utc_now()
    intended_role = (
        (invitation.intended_role or invitation.permitted_role) if invitation else None
    )
    if (
        not invitation
        or invitation.revoked_at is not None
        or invitation.accepted_at is not None
        or (invitation.expires_at and invitation.expires_at.replace(tzinfo=UTC) <= now)
        or intended_role not in INVITATION_ROLES.get(role, set())
        or (
            invitation.invited_email
            and invitation.invited_email.lower() != (email or "").lower()
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Invitation is invalid, expired, already used, or does not match this role",
        )
    return invitation


def _signup_coordinates(data: dict[str, Any]) -> tuple[float, float]:
    try:
        latitude, longitude = float(data.get("latitude")), float(data.get("longitude"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422, detail="Valid latitude and longitude are required"
        )
    if not valid_coordinates(latitude, longitude):
        raise HTTPException(
            status_code=422,
            detail="Coordinates are outside the valid latitude/longitude range",
        )
    return latitude, longitude


def _validate_signup(
    role: str, payload: SignupApplicationCreate, invitation: StaffInvitation | None
) -> None:
    required = {
        "patient": ("first_name", "last_name", "phone", "password", "date_of_birth"),
        "specialist": (
            "full_name",
            "phone",
            "email",
            "password",
            "professional_title",
            "primary_specialty",
            "licence_number",
            "licensing_authority",
            "licence_jurisdiction",
        ),
        "hospital": (
            "legal_name",
            "registration_number",
            "licence_number",
            "regulatory_authority",
            "official_email",
            "administrator_name",
            "password",
            "latitude",
            "longitude",
        ),
        "clinic": (
            "legal_name",
            "clinic_type",
            "registration_number",
            "licence_number",
            "official_email",
            "administrator_name",
            "password",
            "latitude",
            "longitude",
        ),
        "nurse": (
            "full_name",
            "phone",
            "email",
            "password",
            "nursing_category",
            "licence_number",
            "licensing_authority",
            "licence_jurisdiction",
        ),
        "pharmacy": (
            "legal_name",
            "registration_number",
            "licence_number",
            "regulatory_authority",
            "responsible_professional",
            "responsible_professional_licence",
            "official_email",
            "administrator_name",
            "password",
            "latitude",
            "longitude",
        ),
        "laboratory": (
            "legal_name",
            "registration_number",
            "accreditation_number",
            "regulatory_authority",
            "responsible_professional",
            "responsible_professional_licence",
            "official_email",
            "administrator_name",
            "password",
            "latitude",
            "longitude",
        ),
        "hmo": (
            "legal_name",
            "organization_type",
            "registration_number",
            "regulatory_authority",
            "official_email",
            "administrator_name",
            "password",
        ),
        "government": (
            "legal_name",
            "government_level",
            "jurisdiction",
            "official_email",
            "full_name",
            "official_title",
        ),
        "platform-admin": (
            "full_name",
            "email",
            "phone",
            "password",
            "admin_role",
            "mfa_method",
            "security_policy_acceptance",
        ),
    }[role]
    _require_signup_fields(payload, required)
    if role == "platform-admin" and not invitation:
        raise HTTPException(
            status_code=422, detail="A valid single-use invitation is required"
        )
    if role in PROFESSIONAL_SIGNUP_TYPES:
        method = str(
            payload.data.get("onboarding_method")
            or ("INVITATION" if invitation else "JOIN_REQUEST")
        )
        if method not in {"INVITATION", "JOIN_REQUEST"}:
            raise HTTPException(
                status_code=422,
                detail="Choose a hospital invitation or membership request",
            )
        if method == "INVITATION" and not invitation:
            raise HTTPException(
                status_code=422,
                detail="A valid single-use hospital invitation is required",
            )
        if method == "JOIN_REQUEST":
            _require_signup_fields(
                payload,
                (
                    "registered_hospital_id",
                    "department_id",
                    "employment_type",
                    "employee_number",
                ),
            )
    if (
        role == "government"
        and not invitation
        and not payload.data.get("authorization_document_key")
    ):
        raise HTTPException(
            status_code=422,
            detail="A valid invitation or authorization document is required",
        )
    if role == "government":
        email = str(payload.data.get("official_email", payload.email or "")).lower()
        if any(domain in email for domain in ("gmail.com", "yahoo.com", "outlook.com")):
            raise HTTPException(
                status_code=422,
                detail="Government applications require an official domain email",
            )
    if role == "platform-admin":
        requested_role = payload.data.get("admin_role")
        if requested_role not in ADMINISTRATOR_ROLES:
            raise HTTPException(
                status_code=422, detail="Unsupported administrator role"
            )
        invitation_limit = invitation.intended_role if invitation else None
        if (
            invitation_limit in ADMINISTRATOR_ROLES
            and requested_role != invitation_limit
        ):
            raise HTTPException(
                status_code=422,
                detail="Requested administrator role exceeds the invitation scope",
            )


async def _create_signup(
    role: str,
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession,
) -> SignupApplicationResponse:
    invitation = await _validated_invitation(
        session, role, payload.invitation_token, payload.email
    )
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
                destination_hospital = uuid.UUID(
                    str(payload.data.get("registered_hospital_id"))
                )
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=422, detail="Select a registered hospital"
                )
            department_id = str(payload.data.get("department_id") or "").strip()
            membership_role = (
                "nurse"
                if role == "nurse"
                else str(payload.data.get("staff_role") or "specialist").lower()
            )
        if membership_role not in INVITATION_ROLES[role]:
            raise HTTPException(
                status_code=422,
                detail="The staff role is not permitted for this signup",
            )
        hospital = await session.scalar(
            select(Tenant).where(
                Tenant.id == destination_hospital, Tenant.status == "ACTIVE"
            )
        )
        department = await resolve_hospital_department(
            session, destination_hospital, department_id
        )
        if department:
            department_id = department.name
        if not hospital or not department:
            raise HTTPException(
                status_code=422,
                detail="Hospital or department is not registered and active",
            )
    latitude, longitude = (
        _signup_coordinates(payload.data)
        if role in {"hospital", "clinic", "pharmacy", "laboratory"}
        else (None, None)
    )
    filters = [
        condition
        for condition in (
            SignupApplication.email == payload.email if payload.email else None,
            SignupApplication.phone == payload.phone if payload.phone else None,
        )
        if condition is not None
    ]
    if filters and await session.scalar(
        select(SignupApplication).where(
            SignupApplication.application_type == role,
            or_(*filters),
            SignupApplication.status.notin_(["REJECTED", "SUSPENDED"]),
        )
    ):
        raise HTTPException(
            status_code=409,
            detail="An active application already exists for this email or phone",
        )
    account_filters = [
        condition
        for condition in (
            AuthAccount.email == payload.email if payload.email else None,
            AuthAccount.phone == payload.phone if payload.phone else None,
        )
        if condition is not None
    ]
    if (
        role == "patient"
        and account_filters
        and await session.scalar(select(AuthAccount).where(or_(*account_filters)))
    ):
        raise HTTPException(
            status_code=409, detail="An account already exists for this email or phone"
        )
    safe_payload = payload.model_dump(
        exclude={"password", "confirm_password", "invitation_token"}
    )
    application = SignupApplication(
        reference=_signup_reference(),
        application_type=role,
        onboarding_type=SIGNUP_ONBOARDING_TYPES[role],
        status=SIGNUP_PENDING_STATUSES[role],
        email=payload.email or payload.data.get("official_email"),
        phone=payload.phone,
        country=payload.country,
        organization_name=payload.data.get("legal_name"),
        payload_json=json.dumps(safe_payload, default=str),
        password_hash=hash_password(payload.password) if payload.password else None,
        invitation_id=invitation.id if invitation else None,
        consent_version=payload.consent_version,
    )
    session.add(application)
    await session.flush()
    for consent_type, accepted in (
        ("TERMS", payload.accept_terms),
        ("PRIVACY", payload.accept_privacy),
        ("MARKETING", payload.marketing_consent),
    ):
        session.add(
            ConsentRecord(
                signup_application_id=application.id,
                consent_type=consent_type,
                policy_version=payload.consent_version,
                accepted=accepted,
                ip_address=request.client.host if request.client else None,
            )
        )
    session.add(
        ApplicationReviewHistory(
            signup_application_id=application.id,
            previous_status=None,
            new_status=application.status,
        )
    )
    default_tenant_id = uuid.UUID(settings.operational_tenant_id)
    if role == "patient" and not await session.get(Tenant, default_tenant_id):
        session.add(
            Tenant(
                id=default_tenant_id,
                name="ClinicalFlow",
                state_location="Nigeria",
                accepts_patients=True,
                status="ACTIVE",
            )
        )
    if role == "patient" and settings.skip_phone_verification:
        data = json.loads(application.payload_json)
        date_of_birth = (
            datetime.fromisoformat(data["data"]["date_of_birth"])
            if data.get("data", {}).get("date_of_birth")
            else None
        )
        duplicate_key = patient_duplicate_key(
            data.get("first_name", ""), data.get("last_name", ""), date_of_birth
        )
        if await session.scalar(
            select(PatientRegistry)
            .where(PatientRegistry.duplicate_key == duplicate_key)
            .limit(1)
        ):
            raise HTTPException(
                status_code=409,
                detail="A matching patient identity already exists and requires duplicate review",
            )
        account = AuthAccount(
            tenant_id=uuid.UUID(settings.operational_tenant_id),
            role="patient",
            identifier=application.phone,
            password_hash=application.password_hash,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            phone=application.phone,
            email=application.email,
            country_code=country_code_for_name(application.country) or "NG",
            date_of_birth=date_of_birth,
            gender=data.get("data", {}).get("gender"),
            state=data.get("region"),
            lga=data.get("data", {}).get("city"),
            emergency_contact=data.get("data", {}).get("emergency_contact_phone"),
            hmo_provider=data.get("data", {}).get("hmo_provider"),
            blood_group=data.get("data", {}).get("blood_group"),
            genotype=data.get("data", {}).get("genotype"),
            known_allergies=data.get("data", {}).get("known_allergies"),
            current_medications=data.get("data", {}).get("current_medications"),
            card_number=f"SV-{secrets.token_hex(5).upper()}",
            phone_verified_at=utc_now(),
            is_active=True,
        )
        session.add(account)
        await session.flush()
        if settings.supabase_auth_enabled:
            try:
                account.supabase_user_id = await provision_user(
                    email=account.email,
                    phone=account.phone,
                    password=payload.password,
                    metadata={
                        "role": account.role,
                        "application_id": str(application.id),
                    },
                )
            except SupabaseAuthError as exc:
                raise HTTPException(
                    status_code=502, detail="Supabase Auth could not create the account"
                ) from exc
        await ensure_patient_registry(session, account)
        application.account_id, application.status = account.id, "ACTIVE"
        session.add(
            ApplicationReviewHistory(
                signup_application_id=application.id,
                previous_status="PHONE_VERIFICATION_REQUIRED",
                new_status="ACTIVE",
            )
        )
    elif role == "patient":
        verification_code = f"{secrets.randbelow(1_000_000):06d}"
        session.add(
            VerificationEvent(
                signup_application_id=application.id,
                event_type="PHONE_OTP",
                status="PENDING",
                token_hash=token_hash(verification_code),
                expires_at=utc_now() + timedelta(minutes=10),
            )
        )
        session.add(
            OutboxEvent(
                tenant_id=uuid.UUID(settings.operational_tenant_id),
                aggregate_type="SignupApplication",
                aggregate_id=application.id,
                event_type="patient.phone_verification_requested",
                recipient_user_id=None,
                payload_json=json.dumps(
                    {
                        "channel": "SMS",
                        "recipient": payload.phone,
                        "message": f"Your ClinicalFlow verification code is {verification_code}. It expires in 10 minutes.",
                        "subject": "ClinicalFlow phone verification",
                    }
                ),
                classification="RESTRICTED",
                status="PENDING",
            )
        )
    if role in ORGANIZATION_SIGNUP_TYPES:
        organization = OrganizationApplication(
            signup_application_id=application.id,
            legal_name=payload.data.get("legal_name", ""),
            registration_number=payload.data.get("registration_number"),
            licence_number=payload.data.get("licence_number")
            or payload.data.get("accreditation_number"),
            regulatory_authority=payload.data.get("regulatory_authority"),
            latitude=latitude,
            longitude=longitude,
            verification_status=application.status,
        )
        session.add(organization)
        await session.flush()
        if role == "hospital":
            submitted_at = application.submitted_at or utc_now()
            session.add(
                FacilityVerificationCase(
                    signup_application_id=application.id,
                    organization_application_id=organization.id,
                    status="REGISTRY_CHECK_PENDING",
                    priority="STANDARD",
                    submitted_at=submitted_at,
                    review_due_at=review_due_at(submitted_at),
                    last_transition_at=submitted_at,
                    government_check_status="PENDING",
                )
            )
    if role in PROFESSIONAL_SIGNUP_TYPES:
        expiration = payload.data.get("licence_expiration")
        expires_at = datetime.fromisoformat(expiration) if expiration else None
        if expires_at and expires_at.replace(tzinfo=UTC) <= utc_now():
            raise HTTPException(
                status_code=422, detail="Professional licence is expired"
            )
        session.add(
            ProfessionalCredential(
                signup_application_id=application.id,
                licence_number=payload.data["licence_number"],
                licensing_authority=payload.data["licensing_authority"],
                jurisdiction=payload.data["licence_jurisdiction"],
                specialty=payload.data.get("primary_specialty")
                or payload.data.get("nursing_category"),
                expires_at=expires_at,
            )
        )
        if (
            not payload.password
            or not payload.email
            or not destination_hospital
            or not department_id
            or not membership_role
        ):
            raise HTTPException(
                status_code=422,
                detail="Staff account or membership information is incomplete",
            )
        if await session.scalar(
            select(AuthAccount).where(
                or_(
                    AuthAccount.email == payload.email,
                    AuthAccount.phone == payload.phone,
                )
            )
        ):
            raise HTTPException(
                status_code=409,
                detail="A personal account already exists for this email or phone",
            )
        name_parts = (payload.full_name or "").strip().split(maxsplit=1)
        account = AuthAccount(
            tenant_id=uuid.UUID(settings.operational_tenant_id),
            role=membership_role,
            identifier=payload.email,
            password_hash=hash_password(payload.password),
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
            phone=payload.phone,
            email=payload.email,
            specialty=(
                payload.data.get("primary_specialty") if role == "specialist" else None
            ),
            is_active=False,
        )
        session.add(account)
        await session.flush()
        if settings.supabase_auth_enabled:
            try:
                account.supabase_user_id = await provision_user(
                    email=account.email,
                    phone=account.phone,
                    password=payload.password,
                    metadata={
                        "role": account.role,
                        "application_id": str(application.id),
                    },
                )
            except SupabaseAuthError as exc:
                raise HTTPException(
                    status_code=502, detail="Supabase Auth could not create the account"
                ) from exc
        provider_registry = await ensure_provider_registry(session, account)
        provider_registry.licence_jurisdiction = payload.data.get(
            "licence_jurisdiction"
        )
        provider_registry.licence_number = payload.data.get("licence_number")
        provider_registry.verification_status = "PENDING_VERIFICATION"
        specialty_id = (
            invitation.specialty_id
            if invitation and invitation.specialty_id
            else (
                payload.data.get("primary_specialty")
                if role == "specialist"
                else payload.data.get("nursing_focus")
            )
        )
        membership = StaffMembership(
            user_id=account.id,
            hospital_id=destination_hospital,
            department_id=department_id,
            department_ref_id=department.id if department else None,
            role=membership_role,
            specialty_id=specialty_id,
            professional_license_number=payload.data.get("licence_number"),
            verification_status="PENDING_HOSPITAL_APPROVAL",
            employment_status="PENDING",
            is_active=False,
            is_on_duty=False,
            active_from=utc_now(),
        )
        session.add(membership)
        application.account_id = account.id
        if invitation:
            invitation.accepted_at = utc_now()
    for document in payload.data.get("documents", []):
        if (
            not isinstance(document, dict)
            or not document.get("private_storage_key")
            or str(document.get("private_storage_key")).startswith(
                ("http://", "https://")
            )
        ):
            raise HTTPException(
                status_code=422,
                detail="Verification documents must use private storage keys",
            )
        if (
            document.get("content_type")
            not in {"application/pdf", "image/jpeg", "image/png"}
            or not 1 <= int(document.get("size_bytes", 0)) <= 10_000_000
        ):
            raise HTTPException(
                status_code=422,
                detail="Verification document type or size is not allowed",
            )
        session.add(
            VerificationDocument(
                signup_application_id=application.id,
                document_type=document.get("document_type", "OTHER"),
                private_storage_key=document["private_storage_key"],
                original_name=document.get("original_name", "document"),
                content_type=document["content_type"],
                size_bytes=int(document["size_bytes"]),
            )
        )
    issued = None
    if application.status == "ACTIVE" and application.account_id:
        account = await session.get(AuthAccount, application.account_id)
        if account:
            issued = await create_session(
                session,
                account,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
    await session.commit()
    if issued:
        response.set_cookie(
            ACCESS_COOKIE,
            issued.access_token,
            httponly=True,
            samesite="lax",
            secure=settings.environment == "production",
        )
        response.set_cookie(
            REFRESH_COOKIE,
            issued.refresh_token,
            httponly=True,
            samesite="lax",
            secure=settings.environment == "production",
        )
    return SignupApplicationResponse(
        id=application.id,
        reference=application.reference,
        application_type=role,
        onboarding_type=application.onboarding_type,
        status=application.status,
        submitted_at=application.submitted_at,
        login_path=SIGNUP_LOGIN_PATHS[role],
        dashboard_path=(
            SIGNUP_DASHBOARD_PATHS[role] if application.status == "ACTIVE" else None
        ),
    )


async def _verify_patient(
    payload: SignupVerificationRequest,
    response: Response,
    session: AsyncSession,
    event_type: str,
) -> SignupApplicationResponse:
    application = await session.get(SignupApplication, payload.application_id)
    if not application or application.application_type != "patient":
        raise HTTPException(status_code=404, detail="Signup application not found")
    event = await session.scalar(
        select(VerificationEvent)
        .where(
            VerificationEvent.signup_application_id == application.id,
            VerificationEvent.event_type == event_type,
            VerificationEvent.status == "PENDING",
        )
        .order_by(VerificationEvent.created_at.desc())
    )
    if (
        not event
        or not event.token_hash
        or event.token_hash != token_hash(payload.code)
        or (event.expires_at and event.expires_at.replace(tzinfo=UTC) <= utc_now())
    ):
        raise HTTPException(
            status_code=422, detail="Verification code is invalid or expired"
        )
    data = json.loads(application.payload_json)
    if not application.password_hash or not application.phone:
        raise HTTPException(status_code=422, detail="Patient application is incomplete")
    date_of_birth = (
        datetime.fromisoformat(data["data"]["date_of_birth"])
        if data.get("data", {}).get("date_of_birth")
        else None
    )
    duplicate_key = patient_duplicate_key(
        data.get("first_name", ""), data.get("last_name", ""), date_of_birth
    )
    duplicate = await session.scalar(
        select(PatientRegistry)
        .where(PatientRegistry.duplicate_key == duplicate_key)
        .limit(1)
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A matching patient identity already exists and requires duplicate review",
        )
    account = AuthAccount(
        tenant_id=uuid.UUID(settings.operational_tenant_id),
        role="patient",
        identifier=application.phone,
        password_hash=application.password_hash,
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        phone=application.phone,
        email=application.email,
        date_of_birth=date_of_birth,
        gender=data.get("data", {}).get("gender"),
        state=data.get("region"),
        lga=data.get("data", {}).get("city"),
        emergency_contact=data.get("data", {}).get("emergency_contact_phone"),
        hmo_provider=data.get("data", {}).get("hmo_provider"),
        blood_group=data.get("data", {}).get("blood_group"),
        genotype=data.get("data", {}).get("genotype"),
        known_allergies=data.get("data", {}).get("known_allergies"),
        current_medications=data.get("data", {}).get("current_medications"),
        card_number=f"SV-{secrets.token_hex(5).upper()}",
        phone_verified_at=utc_now(),
        is_active=True,
    )
    session.add(account)
    await session.flush()
    await ensure_patient_registry(session, account)
    application.account_id, application.status = account.id, "ACTIVE"
    event.status, event.completed_at = "VERIFIED", utc_now()
    for consent in (
        (
            await session.execute(
                select(ConsentRecord).where(
                    ConsentRecord.signup_application_id == application.id
                )
            )
        )
        .scalars()
        .all()
    ):
        consent.account_id = account.id
    session.add(
        ApplicationReviewHistory(
            signup_application_id=application.id,
            previous_status="PHONE_VERIFICATION_REQUIRED",
            new_status="ACTIVE",
        )
    )
    issued = await create_session(session, account)
    await session.commit()
    _set_session_cookies(response, issued.access_token, issued.refresh_token)
    return SignupApplicationResponse(
        id=application.id,
        reference=application.reference,
        application_type="patient",
        onboarding_type=application.onboarding_type,
        status="ACTIVE",
        submitted_at=application.submitted_at,
        login_path="/login",
        dashboard_path="/dashboard",
    )


async def require_facility_reviewer(
    request: Request, session: AsyncSession, *, supervisor: bool = False
) -> AuthAccount:
    account = await require_roles(request, session, FACILITY_VERIFIER_ROLES)
    if supervisor and account.role != "verification_supervisor":
        raise HTTPException(
            status_code=403, detail="Verification supervisor access required"
        )
    return account


async def _verification_document_access(
    request: Request, session: AsyncSession, document_id: str
) -> tuple[AuthAccount, VerificationDocument]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    try:
        identifier = uuid.UUID(document_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid document ID") from error
    document = await session.scalar(
        select(VerificationDocument)
        .join(
            SignupApplication,
            SignupApplication.id == VerificationDocument.signup_application_id,
        )
        .where(
            VerificationDocument.id == identifier,
            (
                SignupApplication.account_id == account.id
                if account.role != "admin"
                else True
            ),
        )
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return account, document


async def appointment_response(
    session: AsyncSession, appointment: Appointment
) -> AppointmentResponse:
    slot, provider = (
        await session.execute(
            select(ProviderSlot, Provider)
            .join(Provider, Provider.id == ProviderSlot.provider_id)
            .where(ProviderSlot.id == appointment.slot_id)
        )
    ).one()
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


async def persist_routing_decision(
    session: AsyncSession,
    ticket: TicketResponse,
    clinical_route: Any,
    candidates: tuple[Any, ...],
    selected_facility_id: uuid.UUID | None,
    preferred_facility_id: uuid.UUID | None,
    reason: str,
    *,
    patient_country_code: str | None = None,
    route_distance_km: float | None = None,
) -> RoutingDecision:
    selected_country = next(
        (
            str(item.registry.country).upper()
            for item in candidates
            if item.tenant.id == selected_facility_id
        ),
        None,
    )
    decision = RoutingDecision(
        ticket_id=ticket.id,
        patient_owner_tenant_id=ticket.tenant_id,
        selected_facility_id=selected_facility_id,
        required_service=str(clinical_route.target_specialty),
        required_specialty=str(clinical_route.target_specialty),
        urgency=str(clinical_route.derived_urgency),
        status="SELECTED" if selected_facility_id else "NO_SUITABLE_FACILITY",
        selection_reason=reason,
        patient_preference_facility_id=preferred_facility_id,
        patient_country_code=patient_country_code,
        selected_hospital_country_code=selected_country,
        cross_border=bool(
            selected_country
            and patient_country_code
            and selected_country != patient_country_code
        ),
        eligibility_reasons=json.dumps(
            [r for item in candidates if item.eligible for r in item.reasons]
        ),
        rejected_candidates=json.dumps(
            [
                {"facility_id": str(item.tenant.id), "reasons": item.reasons}
                for item in candidates
                if not item.eligible
            ]
        ),
        route_distance_km=route_distance_km,
    )
    session.add(decision)
    await session.flush()
    session.add_all(
        [
            RoutingCandidate(
                routing_decision_id=decision.id,
                facility_id=item.tenant.id,
                rank=item.rank,
                eligible=item.eligible,
                distance_km=item.distance_km,
                suitability_score=item.suitability_score,
                has_required_capability=item.has_required_capability,
                has_emergency_capability=item.has_emergency_capability,
                has_staff_coverage=item.has_staff_coverage,
                has_capacity=item.has_capacity,
                reasons_json=json.dumps(item.reasons),
            )
            for item in candidates
        ]
    )
    await session.commit()
    return decision


async def mark_notification(
    session: AsyncSession, account: AuthAccount, notification_id: str
) -> None:
    try:
        parsed_id = uuid.UUID(notification_id)
    except ValueError:
        parsed_id = None
    if parsed_id:
        memberships = (
            await active_staff_memberships(session, account)
            if account.role != "patient"
            else []
        )
        membership_ids = [membership.id for membership in memberships]
        filters = [
            Notification.recipient_user_id == account.id,
            Notification.recipient_account_id == account.id,
        ]
        if membership_ids:
            filters.append(Notification.recipient_membership_id.in_(membership_ids))
        notification = await session.scalar(
            select(Notification)
            .where(Notification.id == parsed_id, or_(*filters))
            .with_for_update()
        )
        if notification:
            notification.is_read = True
            notification.read_at = utc_now()
            return
    title = f"{account.id}:{notification_id}"
    exists = await session.scalar(
        select(OperationalRecord).where(
            OperationalRecord.tenant_id == account.tenant_id,
            OperationalRecord.entity == "notification",
            OperationalRecord.resource == "read",
            OperationalRecord.title == title,
        )
    )
    if not exists:
        session.add(
            OperationalRecord(
                tenant_id=account.tenant_id,
                entity="notification",
                resource="read",
                title=title,
                description="Notification read marker",
                status="READ",
            )
        )


DOCTOR_RECORD_SECTIONS = {
    "identity",
    "triage",
    "allergies",
    "current_medications",
    "existing_conditions",
    "diagnoses",
    "appointments",
    "clinical_notes",
    "laboratory_results",
    "imaging_results",
    "prescriptions",
    "care_plans",
    "referrals",
    "hmo",
    "emergency_contact",
}
NURSE_RECORD_SECTIONS = {
    "identity",
    "triage",
    "allergies",
    "current_medications",
    "appointments",
    "care_plans",
    "safety_warnings",
}


async def record_access_audit(
    session: AsyncSession,
    request: Request,
    account: AuthAccount,
    membership: StaffMembership | None,
    ticket: Ticket,
    *,
    outcome: str,
    sections: set[str],
    reason: str,
    appointment_id: uuid.UUID | None = None,
    break_glass: bool = False,
) -> None:
    patient = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone
        )
    )
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
        metadata={
            "outcome": outcome,
            "membership_id": str(membership.id) if membership else None,
            "patient_id": str(patient.id) if patient else None,
            "hospital_id": str(ticket_destination_id(ticket)),
            "appointment_id": str(appointment_id) if appointment_id else None,
            "access_reason": reason,
            "record_sections_viewed": sorted(sections),
            "session_id": request.cookies.get(ACCESS_COOKIE, "")[-12:] or None,
            "break_glass_used": break_glass,
        },
    )


async def clinician_record_context(
    session: AsyncSession, request: Request, ticket_id: uuid.UUID
) -> tuple[
    AuthAccount,
    StaffMembership,
    Ticket,
    Appointment | None,
    CareTeamAssignment | None,
    bool,
]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse"})
    memberships = await active_staff_memberships(session, account)
    ticket = None
    membership = None
    for candidate in memberships:
        await apply_tenant_context(session, candidate.hospital_id)
        candidate_ticket = await session.scalar(
            select(Ticket).where(
                Ticket.id == ticket_id, ticket_visible_to_tenant(candidate.hospital_id)
            )
        )
        if (
            candidate_ticket
            and ticket_destination_id(candidate_ticket) == candidate.hospital_id
        ):
            ticket, membership = candidate_ticket, candidate
            break
    if not ticket or not membership:
        await write_audit_log(
            session,
            AuditAction.PATIENT_RECORD_VIEWED,
            actor_id=str(account.id),
            actor_type=account.role.upper(),
            tenant_id=str(account.tenant_id),
            ip_address=request.client.host if request.client else "127.0.0.1",
            resource_type="PatientRecord",
            resource_id=str(ticket_id),
            user_agent=request.headers.get("user-agent"),
            metadata={
                "outcome": "DENIED",
                "access_reason": "NO_ACTIVE_TREATMENT_WORKSPACE",
                "record_sections_viewed": [],
                "break_glass_used": False,
            },
        )
        await session.commit()
        raise HTTPException(
            status_code=404,
            detail="Patient record not found in an active treatment workspace",
        )
    hospital_id = ticket_destination_id(ticket)
    if not membership:
        await record_access_audit(
            session,
            request,
            account,
            None,
            ticket,
            outcome="DENIED",
            sections=set(),
            reason="NO_ACTIVE_MEMBERSHIP",
        )
        await session.commit()
        raise HTTPException(
            status_code=403,
            detail="No active verified membership at the routed hospital",
        )
    appointment = await session.scalar(
        select(Appointment)
        .where(
            Appointment.ticket_id == ticket.id,
            Appointment.hospital_id == hospital_id,
            Appointment.department_id == membership.department_id,
            Appointment.doctor_id == account.id,
            Appointment.staff_membership_id == membership.id,
            Appointment.status == "BOOKED",
        )
        .order_by(Appointment.created_at.desc())
        .limit(1)
    )
    care_assignment = await session.scalar(
        select(CareTeamAssignment)
        .where(
            CareTeamAssignment.ticket_id == ticket.id,
            CareTeamAssignment.hospital_id == hospital_id,
            CareTeamAssignment.department_id == membership.department_id,
            CareTeamAssignment.user_id == account.id,
            CareTeamAssignment.membership_id == membership.id,
            CareTeamAssignment.status == "ACTIVE",
            CareTeamAssignment.starts_at <= utc_now(),
            or_(
                CareTeamAssignment.ends_at.is_(None),
                CareTeamAssignment.ends_at >= utc_now(),
            ),
        )
        .limit(1)
    )
    if ticket.queue_status == "RESOLVED":
        appointment = None
        care_assignment = None
    directly_assigned = (
        account.role in {"doctor", "specialist"}
        and ticket.assigned_specialist_id == account.id
        and ticket.queue_status != "RESOLVED"
        and membership.department_id
        == department_for_specialty(ticket.assigned_specialty)
        and membership.specialty_id == ticket.assigned_specialty
    )
    grant = await session.scalar(
        select(BreakGlassGrant)
        .where(
            BreakGlassGrant.ticket_id == ticket.id,
            BreakGlassGrant.user_id == account.id,
            BreakGlassGrant.membership_id == membership.id,
            BreakGlassGrant.confirmed.is_(True),
            BreakGlassGrant.revoked_at.is_(None),
            BreakGlassGrant.expires_at > utc_now(),
        )
        .order_by(BreakGlassGrant.created_at.desc())
        .limit(1)
    )
    patient_account = await session.scalar(
        select(AuthAccount).where(
            AuthAccount.role == "patient", AuthAccount.phone == ticket.customer_phone
        )
    )
    if patient_account:
        patient_registry = await ensure_patient_registry(session, patient_account)
        consent = await session.scalar(
            select(PatientConsentDirective)
            .where(
                PatientConsentDirective.patient_id == patient_registry.id,
                PatientConsentDirective.purpose == "CARE_DELIVERY",
                PatientConsentDirective.status == "ACTIVE",
            )
            .limit(1)
        )
        if not consent and not grant:
            await record_access_audit(
                session,
                request,
                account,
                membership,
                ticket,
                outcome="DENIED",
                sections=set(),
                reason="PATIENT_CONSENT_WITHDRAWN",
            )
            await session.commit()
            raise HTTPException(
                status_code=403, detail="Patient consent does not permit record access"
            )
    if account.role == "nurse" and not care_assignment and not grant:
        await record_access_audit(
            session,
            request,
            account,
            membership,
            ticket,
            outcome="DENIED",
            sections=set(),
            reason="NO_ASSIGNED_NURSING_DUTY",
        )
        await session.commit()
        raise HTTPException(
            status_code=403,
            detail="An assigned nursing task or care-team responsibility is required",
        )
    if (
        account.role in {"doctor", "specialist"}
        and not appointment
        and not care_assignment
        and not directly_assigned
        and not grant
    ):
        await record_access_audit(
            session,
            request,
            account,
            membership,
            ticket,
            outcome="DENIED",
            sections=set(),
            reason="NO_ACTIVE_TREATMENT_RELATIONSHIP",
        )
        await session.commit()
        raise HTTPException(
            status_code=403, detail="No active treatment relationship for this patient"
        )
    return account, membership, ticket, appointment, care_assignment, bool(grant)


OPERATIONAL_RESOURCES = {
    "dashboard",
    "queue",
    "people",
    "doctors",
    "specialists",
    "appointments",
    "analytics",
    "notifications",
    "settings",
    "schedule",
    "patients",
    "visits",
    "vitals",
    "care-plans",
    "departments",
    "deliveries",
    "inventory",
    "prescriptions",
    "collections",
    "equipment",
    "requests",
    "results",
    "authorizations",
    "claims",
    "facilities",
    "members",
    "payments",
    "utilization",
    "reports",
    "surveillance",
    "messages",
}

SPECIALIST_RESOURCES = {
    "dashboard",
    "queue",
    "patients",
    "appointments",
    "schedule",
    "notes",
    "messages",
    "earnings",
    "notifications",
    "settings",
}


async def require_specialist(request: Request, session: AsyncSession) -> AuthAccount:
    account = await require_account(request, session)
    if account.role not in {"doctor", "specialist"}:
        raise HTTPException(status_code=403, detail="Specialist access required")
    return account


async def require_specialist_workspace(
    request: Request, session: AsyncSession
) -> tuple[AuthAccount, StaffMembership]:
    account = await require_specialist(request, session)
    membership = await require_staff_workspace(
        session, account, roles={"doctor", "specialist"}
    )
    return account, membership


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


__all__ = [name for name in globals() if not name.startswith("__")]
