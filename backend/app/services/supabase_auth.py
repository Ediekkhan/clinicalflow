from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AuthAccount


class SupabaseAuthError(RuntimeError):
    pass


def _base_url() -> str:
    return (settings.supabase_url or "").rstrip("/")


def _headers(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


async def password_login(identifier: str, password: str) -> UUID | None:
    if not settings.supabase_auth_enabled:
        return None
    payload = {"password": password}
    if "@" in identifier:
        payload["email"] = identifier
    else:
        payload["phone"] = identifier
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(f"{_base_url()}/auth/v1/token?grant_type=password", headers=_headers(settings.supabase_anon_key or ""), json=payload)
    if response.status_code >= 400:
        return None
    user_id = response.json().get("user", {}).get("id")
    try:
        return UUID(str(user_id))
    except (ValueError, TypeError):
        return None


async def provision_user(*, email: str | None, phone: str | None, password: str, metadata: dict[str, Any] | None = None) -> UUID | None:
    """Create a Supabase Auth identity. Duplicate identities are reported so
    callers can link an existing account rather than creating a profile copy."""
    if not (settings.supabase_auth_enabled and settings.supabase_service_role_key):
        return None
    identity: dict[str, Any] = {"password": password, "user_metadata": metadata or {}}
    if email:
        identity["email"] = email.strip().lower()
    if phone:
        identity["phone"] = phone
    identity["email_confirm"] = True
    identity["phone_confirm"] = settings.skip_phone_verification
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(f"{_base_url()}/auth/v1/admin/users", headers=_headers(settings.supabase_service_role_key), json=identity)
    if response.status_code >= 400:
        raise SupabaseAuthError(response.text[:500])
    try:
        return UUID(str(response.json()["id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise SupabaseAuthError("Supabase did not return a user id") from exc


def verify_access_token(token: str) -> UUID | None:
    if not (settings.supabase_jwt_secret and settings.supabase_url):
        return None
    try:
        claims = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated", issuer=f"{settings.supabase_url.rstrip('/')}/auth/v1")
        return UUID(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None


async def account_for_supabase_token(db: AsyncSession, token: str) -> AuthAccount | None:
    user_id = verify_access_token(token)
    if not user_id:
        return None
    return await db.scalar(select(AuthAccount).where(AuthAccount.supabase_user_id == user_id, AuthAccount.is_active.is_(True)))
