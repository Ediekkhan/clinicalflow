from uuid import UUID

from fastapi import Request

from app.core.config import get_settings


def current_tenant_id(request: Request) -> UUID:
    tenant_id = getattr(request.state, "tenant_id", None) or request.headers.get("X-Tenant-Id")
    if tenant_id:
        return UUID(str(tenant_id))
    return get_settings().demo_tenant_id


def current_staff_id(request: Request) -> UUID | None:
    staff_id = getattr(request.state, "staff_id", None)
    return UUID(str(staff_id)) if staff_id else None
