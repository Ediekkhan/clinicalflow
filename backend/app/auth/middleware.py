from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth.jwt_handler import ACCESS_COOKIE, verify_token


PUBLIC_ROUTES = [
    "/api/v1/auth/patient/signup",
    "/api/v1/auth/patient/login",
    "/api/v1/auth/specialist/login",
    "/api/v1/auth/staff/login",
    "/api/v1/auth/clinics",
    "/api/v1/auth/refresh",
    "/api/v1/health",
    "/api/v1/webhooks",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or any(path.startswith(route) for route in PUBLIC_ROUTES):
            return await call_next(request)

        token = request.cookies.get(ACCESS_COOKIE)
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        if not token:
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})

        try:
            payload = verify_token(token)
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Token invalid or expired"})

        request.state.user = payload
        request.state.user_type = payload.get("type")
        request.state.tenant_id = payload.get("tenant_id")
        request.state.staff_id = payload.get("sub") if payload.get("type") == "STAFF" else None
        request.state.staff_role = payload.get("role")
        request.state.patient_id = payload.get("sub") if payload.get("type") == "PATIENT" else None
        request.state.specialist_id = payload.get("sub") if payload.get("type") == "SPECIALIST" else None
        return await call_next(request)
