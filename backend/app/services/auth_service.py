from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AuthAccount, AuthSession, Tenant

ACCESS_COOKIE = "synaptiverse_access"
REFRESH_COOKIE = "synaptiverse_refresh"
PASSWORD_ITERATIONS = 600_000


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), actual_salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.urlsafe_b64encode(actual_salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hash_password(password, salt=base64.urlsafe_b64decode(salt)).split("$", 3)[3]
        return int(iterations) == PASSWORD_ITERATIONS and hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_tenant_id(token: str) -> UUID | None:
    try:
        tenant, secret = token.split(".", 1)
        return UUID(tenant) if secret else None
    except (ValueError, AttributeError):
        return None


async def apply_tenant_context(db: AsyncSession, tenant_id: UUID) -> None:
    db.info["tenant_id"] = str(tenant_id)
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SET LOCAL app.current_tenant_id = :tenant_id"), {"tenant_id": str(tenant_id)})


@dataclass(frozen=True)
class IssuedSession:
    session: AuthSession
    access_token: str
    refresh_token: str


async def create_session(db: AsyncSession, account: AuthAccount) -> IssuedSession:
    access_token = f"{account.tenant_id}.{secrets.token_urlsafe(48)}"
    refresh_token = f"{account.tenant_id}.{secrets.token_urlsafe(64)}"
    now = utc_now()
    session = AuthSession(
        account_id=account.id,
        tenant_id=account.tenant_id,
        access_token_hash=token_hash(access_token),
        refresh_token_hash=token_hash(refresh_token),
        access_expires_at=now + timedelta(minutes=settings.auth_access_minutes),
        refresh_expires_at=now + timedelta(days=settings.auth_refresh_days),
    )
    db.add(session)
    await db.flush()
    return IssuedSession(session, access_token, refresh_token)


async def find_account(db: AsyncSession, role: str, identifier: str, tenant_id: UUID) -> AuthAccount | None:
    await apply_tenant_context(db, tenant_id)
    result = await db.execute(
        select(AuthAccount).where(
            AuthAccount.tenant_id == tenant_id,
            AuthAccount.role == role,
            AuthAccount.identifier == identifier.strip().lower(),
            AuthAccount.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def account_for_access_token(db: AsyncSession, token: str) -> tuple[AuthAccount, AuthSession] | None:
    tenant_id = token_tenant_id(token)
    if not tenant_id:
        return None
    await apply_tenant_context(db, tenant_id)
    result = await db.execute(
        select(AuthAccount, AuthSession)
        .join(AuthSession, AuthSession.account_id == AuthAccount.id)
        .where(AuthSession.access_token_hash == token_hash(token), AuthSession.revoked_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        return None
    account, auth_session = row
    if auth_session.access_expires_at.replace(tzinfo=UTC) <= utc_now() or not account.is_active:
        return None
    return account, auth_session


async def session_for_refresh_token(db: AsyncSession, token: str) -> tuple[AuthAccount, AuthSession] | None:
    tenant_id = token_tenant_id(token)
    if not tenant_id:
        return None
    await apply_tenant_context(db, tenant_id)
    result = await db.execute(
        select(AuthAccount, AuthSession)
        .join(AuthSession, AuthSession.account_id == AuthAccount.id)
        .where(AuthSession.refresh_token_hash == token_hash(token), AuthSession.revoked_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        return None
    account, auth_session = row
    if auth_session.refresh_expires_at.replace(tzinfo=UTC) <= utc_now() or not account.is_active:
        return None
    return account, auth_session


async def seed_demo_accounts(db: AsyncSession) -> None:
    tenant_id = UUID("11111111-1111-1111-1111-111111111111")
    if not await db.get(Tenant, tenant_id):
        db.add(Tenant(id=tenant_id, name="SynaptiVerse Demo Clinic", state_location="Akwa Ibom", latitude=5.0380, longitude=7.9090, accepts_patients=True))
        await db.flush()
    else:
        tenant = await db.get(Tenant, tenant_id)
        if tenant and (tenant.latitude is None or tenant.longitude is None):
            tenant.latitude = 5.0380
            tenant.longitude = 7.9090
            tenant.accepts_patients = True
    seeds = (
        dict(role="patient", identifier="+2348012345678", first_name="Ada", last_name="Okafor", phone="+2348012345678", card_number="SV-1001"),
        dict(role="specialist", identifier="dr.ada@example.com", first_name="Ada", last_name="Okafor", email="dr.ada@example.com", specialty="General Medicine"),
        dict(role="nurse", identifier="uyo-family:nurse", first_name="Ini", last_name="Etim"),
        dict(role="admin", identifier="uyo-family:admin", first_name="System", last_name="Administrator"),
        dict(role="doctor", identifier="uyo-family:doctor", first_name="Bassey", last_name="Udo", specialty="General Medicine"),
        dict(role="hospital_admin", identifier="uyo-family:hospital_admin", first_name="Grace", last_name="Akpan"),
    )
    for seed in seeds:
        if not await find_account(db, seed["role"], seed["identifier"], tenant_id):
            credential = {"nurse": "2468", "admin": "1357"}.get(seed["role"], "Password123!")
            db.add(AuthAccount(tenant_id=tenant_id, password_hash=hash_password(credential), **seed))
    await db.commit()
