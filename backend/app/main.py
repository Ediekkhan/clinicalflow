from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    appointments,
    auth,
    compliance,
    health,
    location,
    notifications,
    specialists,
    tickets,
    triage,
    webhooks,
    ws,
)
from app.core.config import get_settings
from app.core.middleware import TenantContextMiddleware
from app.middleware.audit_middleware import AuditMetadataMiddleware
from app.middleware.rate_limiter import RedisRateLimiterMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description=(
        "B2B multi-tenant clinical triage and scheduling platform optimized "
        "for Nigerian clinic operations."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Tenant-Id"],
    expose_headers=["X-Request-ID", "Retry-After"],
    max_age=600,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMetadataMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(RedisRateLimiterMiddleware)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(triage.router, prefix=settings.api_prefix)
app.include_router(tickets.router, prefix=settings.api_prefix)
app.include_router(appointments.router, prefix=settings.api_prefix)
app.include_router(specialists.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(location.router, prefix=settings.api_prefix)
app.include_router(webhooks.router, prefix=settings.api_prefix)
app.include_router(ws.router, prefix=settings.api_prefix)
