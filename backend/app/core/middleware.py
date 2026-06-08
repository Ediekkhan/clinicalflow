from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import resolve_request_principal


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Attaches the current tenant to the request before route dependencies run.

    Tokens are preferred for authenticated dashboards; webhook integrations may
    also pass `X-Tenant-Id` because Meta/SMS callbacks are often signed at the
    gateway edge before reaching this service.
    """

    async def dispatch(self, request: Request, call_next):
        principal = resolve_request_principal(request)
        request.state.tenant_id = principal.tenant_id
        request.state.staff_id = principal.staff_id
        request.state.staff_role = principal.role
        return await call_next(request)

