from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuditMetadataMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.audit_ip = request.client.host if request.client else "unknown"
        request.state.audit_user_agent = request.headers.get("user-agent")
        return await call_next(request)
