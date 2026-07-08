from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, Request, WebSocket, status

from app.auth.jwt_handler import create_access_token, verify_token
from app.auth.password_handler import hash_password, verify_password
from app.auth.pin_handler import hash_pin, verify_pin
from app.core.config import get_settings


@dataclass(frozen=True)
class TenantPrincipal:
    tenant_id: UUID
    staff_id: UUID | None = None
    role: str | None = None
    user_type: str | None = None


def decode_principal_from_token(token: str) -> TenantPrincipal:
    payload = verify_token(token)
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant claim.")
    staff_id = payload.get("sub") if payload.get("type") == "STAFF" else None
    return TenantPrincipal(
        tenant_id=UUID(tenant_id),
        staff_id=UUID(staff_id) if staff_id else None,
        role=payload.get("role"),
        user_type=payload.get("type"),
    )


def issue_staff_token(tenant_id: UUID, staff_id: UUID, role: str) -> str:
    return create_access_token(
        subject=str(staff_id),
        user_type="STAFF",
        extra_claims={"tenant_id": str(tenant_id), "role": role},
        expires_delta=timedelta(hours=8),
    )


def issue_patient_token(tenant_id: UUID, patient_id: UUID) -> str:
    return create_access_token(
        subject=str(patient_id),
        user_type="PATIENT",
        extra_claims={"tenant_id": str(tenant_id)},
        expires_delta=timedelta(hours=8),
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


__all__ = [
    "TenantPrincipal",
    "decode_principal_from_token",
    "hash_password",
    "hash_pin",
    "issue_patient_token",
    "issue_staff_token",
    "resolve_request_principal",
    "resolve_websocket_principal",
    "verify_password",
    "verify_pin",
]
