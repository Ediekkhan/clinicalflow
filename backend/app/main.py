from contextlib import asynccontextmanager
import json
import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.clinical_routes import register_clinical_routes
from app.sector_routes import register_sector_routes
from app.terminology_routes import register_terminology_routes
from app.models import Base, FacilityService, Provider, Tenant
from app.routes import register_routes, triage_manager
from app.services.auth_service import seed_demo_accounts
from app.services.scheduling_service import seed_demo_schedule
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.knowledge_graph import SYMPTOM_ALIASES
from app.services.registry_service import ensure_facility_registry
from app.services.country_policy import ensure_nigeria_country_pack
from app.services.redis_service import RedisInfrastructure
from app.services.outbox_worker import OutboxWorker, worker_status
from app.services.provider_adapters import provider_health
from uuid import UUID


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")
logger = logging.getLogger("synaptiverse")
request_metrics = {"requests_total": 0, "errors_total": 0}


async def ensure_sqlite_additive_schema(engine) -> None:
    async with engine.begin() as conn:
        def table_columns(sync_conn, table_name: str) -> set[str]:
            inspector = inspect(sync_conn)
            if table_name not in inspector.get_table_names():
                return set()
            return {column["name"] for column in inspector.get_columns(table_name)}

        tenant_columns = await conn.run_sync(table_columns, "tenants")
        ticket_columns = await conn.run_sync(table_columns, "tickets")
        provider_columns = await conn.run_sync(table_columns, "providers")
        session_columns = await conn.run_sync(table_columns, "auth_sessions")
        appointment_columns = await conn.run_sync(table_columns, "appointments")
        notification_columns = await conn.run_sync(table_columns, "notifications")
        auth_account_columns = await conn.run_sync(table_columns, "auth_accounts")
        staff_membership_columns = await conn.run_sync(table_columns, "staff_memberships")
        staff_invitation_columns = await conn.run_sync(table_columns, "staff_invitations")
        if tenant_columns and "latitude" not in tenant_columns:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN latitude FLOAT"))
        if tenant_columns and "longitude" not in tenant_columns:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN longitude FLOAT"))
        if tenant_columns and "accepts_patients" not in tenant_columns:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN accepts_patients BOOLEAN NOT NULL DEFAULT 1"))
        if auth_account_columns and "supabase_user_id" not in auth_account_columns:
            await conn.execute(text("ALTER TABLE auth_accounts ADD COLUMN supabase_user_id CHAR(32)"))
            await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_auth_accounts_supabase_user_id ON auth_accounts (supabase_user_id)"))
        if ticket_columns and "patient_latitude" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN patient_latitude FLOAT"))
        if ticket_columns and "patient_longitude" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN patient_longitude FLOAT"))
        if ticket_columns and "routed_tenant_id" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN routed_tenant_id CHAR(32)"))
        if ticket_columns and "route_distance_km" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN route_distance_km FLOAT"))
        if ticket_columns and "terminology_release_id" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN terminology_release_id CHAR(32)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_terminology_release_id ON tickets (terminology_release_id)"))
        if ticket_columns:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_routed_tenant_id ON tickets (routed_tenant_id)"))
            await conn.execute(text("UPDATE tickets SET routed_tenant_id = tenant_id WHERE routed_tenant_id IS NULL"))
        if session_columns and "selected_membership_id" not in session_columns:
            await conn.execute(text("ALTER TABLE auth_sessions ADD COLUMN selected_membership_id CHAR(32)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_auth_sessions_selected_membership_id ON auth_sessions (selected_membership_id)"))
        if provider_columns and "doctor_id" not in provider_columns:
            await conn.execute(text("ALTER TABLE providers ADD COLUMN doctor_id CHAR(32)"))
        if provider_columns and "max_daily_capacity" not in provider_columns:
            await conn.execute(text("ALTER TABLE providers ADD COLUMN max_daily_capacity INTEGER NOT NULL DEFAULT 12"))
        if appointment_columns and "department_id" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN department_id VARCHAR(128)"))
        if appointment_columns and "staff_membership_id" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN staff_membership_id CHAR(32)"))
        if appointment_columns and "hospital_id" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN hospital_id CHAR(32)"))
        if appointment_columns and "doctor_id" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN doctor_id CHAR(32)"))
        if appointment_columns and "specialty_id" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN specialty_id VARCHAR(128)"))
        if appointment_columns and "urgency" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN urgency VARCHAR(32)"))
        if appointment_columns and "starts_at" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN starts_at DATETIME"))
        if appointment_columns and "ends_at" not in appointment_columns:
            await conn.execute(text("ALTER TABLE appointments ADD COLUMN ends_at DATETIME"))
        if appointment_columns:
            await conn.execute(text("UPDATE appointments SET hospital_id = tenant_id WHERE hospital_id IS NULL"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_hospital_doctor ON appointments (hospital_id, doctor_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_department_id ON appointments (department_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_appointments_staff_membership_id ON appointments (staff_membership_id)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS hospital_doctor_memberships (id CHAR(32) PRIMARY KEY, hospital_id CHAR(32) NOT NULL, doctor_id CHAR(32) NOT NULL, specialty_id VARCHAR(128) NOT NULL, verification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING', employment_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', notification_preferences TEXT, is_active BOOLEAN NOT NULL DEFAULT 1, active_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, active_until DATETIME, UNIQUE (hospital_id, doctor_id, specialty_id))"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospital_doctor_memberships_hospital_specialty ON hospital_doctor_memberships (hospital_id, specialty_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospital_doctor_memberships_doctor ON hospital_doctor_memberships (doctor_id)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS staff_memberships (id CHAR(32) PRIMARY KEY, user_id CHAR(32) NOT NULL, hospital_id CHAR(32) NOT NULL, department_id VARCHAR(128) NOT NULL, role VARCHAR(32) NOT NULL, specialty_id VARCHAR(128), professional_license_number VARCHAR(128), verification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING', employment_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', notification_preferences TEXT, is_active BOOLEAN NOT NULL DEFAULT 1, is_on_duty BOOLEAN NOT NULL DEFAULT 0, daily_capacity INTEGER NOT NULL DEFAULT 12, active_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, active_until DATETIME, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (user_id, hospital_id, department_id, role))"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_memberships_user ON staff_memberships (user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_memberships_hospital_department ON staff_memberships (hospital_id, department_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_memberships_assignment ON staff_memberships (hospital_id, department_id, specialty_id, role)"))
        if staff_membership_columns and "daily_capacity" not in staff_membership_columns:
            await conn.execute(text("ALTER TABLE staff_memberships ADD COLUMN daily_capacity INTEGER NOT NULL DEFAULT 12"))
        for column_name in ("department_ref_id", "specialty_ref_id", "legacy_doctor_membership_id"):
            if staff_membership_columns and column_name not in staff_membership_columns:
                await conn.execute(text(f"ALTER TABLE staff_memberships ADD COLUMN {column_name} CHAR(32)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS specialties (id CHAR(32) PRIMARY KEY, code VARCHAR(64) NOT NULL UNIQUE, name VARCHAR(128) NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_specialties_status_name ON specialties (status, name)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS clinical_privileges (id CHAR(32) PRIMARY KEY, membership_id CHAR(32) NOT NULL, code VARCHAR(128) NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', granted_by_account_id CHAR(32), granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at DATETIME, revoked_at DATETIME, UNIQUE (membership_id, code))"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clinical_privileges_membership_status ON clinical_privileges (membership_id, status)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS hospital_departments (id CHAR(32) PRIMARY KEY, hospital_id CHAR(32) NOT NULL, name VARCHAR(128) NOT NULL, code VARCHAR(64) NOT NULL, description TEXT, status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', coordinator_membership_id CHAR(32), capacity INTEGER, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE (hospital_id, code))"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hospital_departments_hospital_status ON hospital_departments (hospital_id, status)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS provider_availability (id CHAR(32) PRIMARY KEY, membership_id CHAR(32) NOT NULL, hospital_id CHAR(32) NOT NULL, department_id VARCHAR(128) NOT NULL, starts_at DATETIME NOT NULL, ends_at DATETIME NOT NULL, status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE', maximum_appointments INTEGER NOT NULL DEFAULT 12, booked_appointments INTEGER NOT NULL DEFAULT 0, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_provider_availability_membership_start ON provider_availability (membership_id, starts_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_provider_availability_hospital_department ON provider_availability (hospital_id, department_id, status)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS staff_invitations (id CHAR(32) PRIMARY KEY, hospital_id CHAR(32) NOT NULL, department_id VARCHAR(128) NOT NULL, permitted_role VARCHAR(32) NOT NULL, invitation_code VARCHAR(128) NOT NULL UNIQUE, invited_email VARCHAR(255), expires_at DATETIME, accepted_at DATETIME, created_by_account_id CHAR(32), created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_staff_invitations_hospital_department ON staff_invitations (hospital_id, department_id)"))
        for column_name, column_type in (
            ("token_hash", "VARCHAR(64)"), ("organization_id", "CHAR(32)"), ("invited_phone", "VARCHAR(32)"),
            ("intended_role", "VARCHAR(32)"), ("specialty_id", "VARCHAR(128)"),
            ("employment_type", "VARCHAR(64)"), ("revoked_at", "DATETIME"), ("invited_by", "CHAR(32)"),
        ):
            if staff_invitation_columns and column_name not in staff_invitation_columns:
                await conn.execute(text(f"ALTER TABLE staff_invitations ADD COLUMN {column_name} {column_type}"))
        await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_staff_invitations_token_hash ON staff_invitations (token_hash)"))
        await conn.execute(text("CREATE TABLE IF NOT EXISTS notifications (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32) NOT NULL, recipient_account_id CHAR(32), recipient_role VARCHAR(32) NOT NULL, appointment_id CHAR(32), ticket_id CHAR(32), event_type VARCHAR(64) NOT NULL, title VARCHAR(255) NOT NULL, body TEXT, payload_json TEXT, is_read BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_tenant_recipient ON notifications (tenant_id, recipient_account_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_appointment ON notifications (appointment_id)"))
        if notification_columns and "recipient_user_id" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN recipient_user_id CHAR(32)"))
        if notification_columns and "recipient_membership_id" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN recipient_membership_id CHAR(32)"))
        if notification_columns and "hospital_id" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN hospital_id CHAR(32)"))
        if notification_columns and "department_id" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN department_id VARCHAR(128)"))
        if notification_columns and "priority" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN priority VARCHAR(32) NOT NULL DEFAULT 'NORMAL'"))
        if notification_columns and "read_at" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN read_at DATETIME"))
        if notification_columns and "acknowledged_at" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN acknowledged_at DATETIME"))
        if notification_columns and "acknowledged_by_account_id" not in notification_columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN acknowledged_by_account_id CHAR(32)"))
        if notification_columns:
            await conn.execute(text("UPDATE notifications SET recipient_user_id = recipient_account_id WHERE recipient_user_id IS NULL"))
            await conn.execute(text("UPDATE notifications SET hospital_id = tenant_id WHERE hospital_id IS NULL"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_recipient_user ON notifications (recipient_user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_recipient_membership ON notifications (recipient_membership_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_workspace ON notifications (hospital_id, department_id)"))


async def seed_facility_registry_compatibility(session) -> None:
    for tenant in list((await session.execute(select(Tenant))).scalars().all()):
        registry = await ensure_facility_registry(session, tenant)
        if str(tenant.id) == settings.default_tenant_id:
            registry.emergency_capable = True
        specialties = list((await session.execute(select(Provider.specialty).where(Provider.tenant_id == tenant.id, Provider.is_active.is_(True)).distinct())).scalars().all())
        for specialty in specialties:
            exists = await session.scalar(select(FacilityService.id).where(FacilityService.facility_registry_id == registry.id, FacilityService.service_code == specialty, FacilityService.specialty_code == specialty))
            if not exists:
                session.add(FacilityService(facility_registry_id=registry.id, service_code=specialty, specialty_code=specialty, status="ACTIVE"))
    await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = create_async_engine(settings.database_url, echo=False, future=True)
    app.state.session_factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    if settings.auto_create_schema:
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        if app.state.engine.dialect.name == "sqlite":
            await ensure_sqlite_additive_schema(app.state.engine)
    if settings.fixtures_enabled:
        async with app.state.session_factory() as session:
            await seed_demo_accounts(session)
        async with app.state.session_factory() as session:
            await seed_demo_schedule(session, UUID(settings.default_tenant_id))
    async with app.state.session_factory() as session:
        await seed_facility_registry_compatibility(session)
    async with app.state.session_factory() as session:
        await ensure_nigeria_country_pack(session)
        await session.commit()
    app.state.redis = RedisInfrastructure(
        enabled=settings.redis_enabled,
        url=settings.redis_url,
        key_prefix=settings.redis_key_prefix,
    )
    await app.state.redis.start(triage_manager.broadcast_local)
    await app.state.redis.set_json("clinical:symptom_aliases", SYMPTOM_ALIASES, ttl_seconds=86400)
    triage_manager.broker = app.state.redis
    app.state.knowledge_graph = KnowledgeGraphService(
        enabled=settings.neo4j_enabled,
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
        cache=app.state.redis,
    )
    await app.state.knowledge_graph.start()
    app.state.outbox_worker = None
    if settings.environment != "production":
        app.state.outbox_worker = OutboxWorker(app.state.session_factory)
        await app.state.outbox_worker.start()
    yield
    await app.state.outbox_worker.stop()
    await app.state.knowledge_graph.close()
    await app.state.redis.close()
    triage_manager.broker = None
    await app.state.engine.dispose()


app = FastAPI(title="SynaptiVerse API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_clinical_routes(app)
register_sector_routes(app)
register_terminology_routes(app)
register_routes(app)


@app.middleware("http")
async def structured_request_logging(request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    started = time.perf_counter()
    request_metrics["requests_total"] += 1
    try:
        response = await call_next(request)
    except Exception:
        request_metrics["errors_total"] += 1
        logger.exception(json.dumps({"event": "request.failed", "request_id": request_id, "method": request.method}))
        raise
    if response.status_code >= 500:
        request_metrics["errors_total"] += 1
    response.headers["x-request-id"] = request_id
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
    response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=(self)"
    response.headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
    route = request.scope.get("route")
    logger.info(json.dumps({"event": "request.completed", "request_id": request_id, "method": request.method, "route": getattr(route, "path", "unmatched"), "status": response.status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}))
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    database_status = "connected"
    outbox_pending = None
    try:
        async with app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
            outbox_pending = (await session.scalar(text("SELECT COUNT(*) FROM outbox_events WHERE status = 'PENDING'"))) or 0
    except Exception:
        database_status = "unavailable"
    return {
        "status": "ok" if database_status == "connected" else "degraded",
        "service": "synaptiverse",
        "dependencies": {
            "database": database_status,
            "redis": "connected" if app.state.redis.available else "degraded-local",
            "neo4j": "connected" if app.state.knowledge_graph.available else "degraded-fallback",
            "worker": worker_status(getattr(app.state, "outbox_worker", None)),
            "outbox_pending": outbox_pending,
            "providers": provider_health(),
        },
    }


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    body = "\n".join([f"synaptiverse_requests_total {request_metrics['requests_total']}", f"synaptiverse_errors_total {request_metrics['errors_total']}"]) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")

