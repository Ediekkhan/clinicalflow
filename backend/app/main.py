from contextlib import asynccontextmanager
import json
import logging
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.models import Base
from app.routes import register_routes, triage_manager
from app.services.auth_service import seed_demo_accounts
from app.services.scheduling_service import seed_demo_schedule
from app.services.knowledge_graph import KnowledgeGraphService
from app.services.knowledge_graph import SYMPTOM_ALIASES
from app.services.redis_service import RedisInfrastructure
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
        if tenant_columns and "latitude" not in tenant_columns:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN latitude FLOAT"))
        if tenant_columns and "longitude" not in tenant_columns:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN longitude FLOAT"))
        if tenant_columns and "accepts_patients" not in tenant_columns:
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN accepts_patients BOOLEAN NOT NULL DEFAULT 1"))
        if ticket_columns and "patient_latitude" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN patient_latitude FLOAT"))
        if ticket_columns and "patient_longitude" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN patient_longitude FLOAT"))
        if ticket_columns and "routed_tenant_id" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN routed_tenant_id CHAR(32)"))
        if ticket_columns and "route_distance_km" not in ticket_columns:
            await conn.execute(text("ALTER TABLE tickets ADD COLUMN route_distance_km FLOAT"))
        if ticket_columns:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_routed_tenant_id ON tickets (routed_tenant_id)"))
            await conn.execute(text("UPDATE tickets SET routed_tenant_id = tenant_id WHERE routed_tenant_id IS NULL"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = create_async_engine(settings.database_url, echo=False, future=True)
    app.state.session_factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    if settings.auto_create_schema:
        async with app.state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        if app.state.engine.dialect.name == "sqlite":
            await ensure_sqlite_additive_schema(app.state.engine)
    async with app.state.session_factory() as session:
        await seed_demo_accounts(session)
    async with app.state.session_factory() as session:
        await seed_demo_schedule(session, UUID(settings.default_tenant_id))
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
    yield
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
    route = request.scope.get("route")
    logger.info(json.dumps({"event": "request.completed", "request_id": request_id, "method": request.method, "route": getattr(route, "path", "unmatched"), "status": response.status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}))
    return response


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "synaptiverse",
        "dependencies": {
            "redis": "connected" if app.state.redis.available else "degraded-local",
            "neo4j": "connected" if app.state.knowledge_graph.available else "degraded-fallback",
        },
    }


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    body = "\n".join([f"synaptiverse_requests_total {request_metrics['requests_total']}", f"synaptiverse_errors_total {request_metrics['errors_total']}"]) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")
