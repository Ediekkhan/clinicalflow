from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, Request, WebSocket, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class TenantPrincipal:
    tenant_id: UUID
    staff_id: UUID | None = None
    role: str | None = None


def hash_pin(pin: str) -> str:
    if len(pin) != 4 or not pin.isdigit():
        raise ValueError("PIN must be exactly four digits.")
    return pwd_context.hash(pin)


def verify_pin(pin: str, hashed_pin: str) -> bool:
    return pwd_context.verify(pin, hashed_pin)


def decode_principal_from_token(token: str) -> TenantPrincipal:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant token.",
        ) from exc

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant claim.")
    staff_id = payload.get("staff_id")
    return TenantPrincipal(
        tenant_id=UUID(tenant_id),
        staff_id=UUID(staff_id) if staff_id else None,
        role=payload.get("role"),
    )


def issue_staff_token(tenant_id: UUID, staff_id: UUID, role: str) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "tenant_id": str(tenant_id),
            "staff_id": str(staff_id),
            "role": role,
            "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def issue_patient_token(tenant_id: UUID, patient_id: UUID) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "tenant_id": str(tenant_id),
            "patient_id": str(patient_id),
            "role": "PATIENT",
            "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def resolve_request_principal(request: Request) -> TenantPrincipal:
    settings = get_settings()
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return decode_principal_from_token(authorization.split(" ", 1)[1])

    tenant_header = request.headers.get("x-tenant-id")
    staff_header = request.headers.get("x-staff-id")
    role_header = request.headers.get("x-staff-role")
    return TenantPrincipal(
        tenant_id=UUID(tenant_header) if tenant_header else settings.demo_tenant_id,
        staff_id=UUID(staff_header) if staff_header else None,
        role=role_header,
    )


def resolve_websocket_principal(websocket: WebSocket) -> TenantPrincipal:
    settings = get_settings()
    token = websocket.query_params.get("token")
    if token:
        return decode_principal_from_token(token)

    tenant_query = websocket.query_params.get("tenant_id")
    return TenantPrincipal(
        tenant_id=UUID(tenant_query) if tenant_query else settings.demo_tenant_id,
    )
