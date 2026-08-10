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
from app.models import (
    AuthAccount,
    AuthSession,
    FacilityRegistry,
    GovernmentAuthority,
    GovernmentUserScope,
    PayerOrganization,
    StaffMembership,
    Tenant,
)
from app.services.supabase_auth import account_for_supabase_token

ACCESS_COOKIE = "clinicalflow_access"
REFRESH_COOKIE = "clinicalflow_refresh"
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
        await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"), {"tenant_id": str(tenant_id)})


@dataclass(frozen=True)
class IssuedSession:
    session: AuthSession
    access_token: str
    refresh_token: str


async def create_session(db: AsyncSession, account: AuthAccount, *, ip_address: str | None = None, user_agent: str | None = None) -> IssuedSession:
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
        ip_address=ip_address,
        user_agent=user_agent,
        last_seen_at=now,
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
    supabase_account = await account_for_supabase_token(db, token)
    if supabase_account:
        return supabase_account, None  # type: ignore[return-value]
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
        db.add(Tenant(id=tenant_id, name="ClinicalFlow Demo Clinic", state_location="Akwa Ibom", latitude=5.0380, longitude=7.9090, accepts_patients=True))
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
        dict(role="nurse", identifier="uyo-family:nurse", first_name="Ini", last_name="Etim", email="nurse.ini@example.com"),
        dict(role="admin", identifier="uyo-family:admin", first_name="System", last_name="Administrator"),
        dict(role="doctor", identifier="doctor.bassey@example.com", first_name="Bassey", last_name="Udo", email="doctor.bassey@example.com", specialty="General Medicine"),
        dict(role="hospital_admin", identifier="admin.grace@example.com", first_name="Grace", last_name="Akpan", email="admin.grace@example.com"),
    )
    for seed in seeds:
        if not await find_account(db, seed["role"], seed["identifier"], tenant_id):
            credential = {"nurse": "2468", "admin": "1357"}.get(seed["role"], "Password123!")
            db.add(AuthAccount(tenant_id=tenant_id, password_hash=hash_password(credential), **seed))
    await db.flush()
    staff_accounts = list((await db.execute(select(AuthAccount).where(AuthAccount.tenant_id == tenant_id, AuthAccount.role.in_(["doctor", "specialist", "nurse", "hospital_admin"])))).scalars().all())
    for account in staff_accounts:
        department = account.specialty or "General Medicine"
        existing_membership = await db.scalar(select(StaffMembership).where(StaffMembership.user_id == account.id, StaffMembership.hospital_id == tenant_id, StaffMembership.department_id == department, StaffMembership.role == account.role))
        if not existing_membership:
            db.add(StaffMembership(user_id=account.id, hospital_id=tenant_id, department_id=department, role=account.role, specialty_id=account.specialty, verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=utc_now() - timedelta(days=1)))
    sector_fixtures = (
        (UUID("22222222-2222-2222-2222-222222222222"), "ClinicalFlow Test Pharmacy", "pharmacy", "pharmacy@example.com"),
        (UUID("33333333-3333-3333-3333-333333333333"), "ClinicalFlow Test Laboratory", "laboratory", "laboratory@example.com"),
        (UUID("44444444-4444-4444-4444-444444444444"), "ClinicalFlow Test HMO", "hmo", "hmo@example.com"),
        (UUID("55555555-5555-5555-5555-555555555555"), "ClinicalFlow Test Health Authority", "government", "government@example.com"),
    )
    sector_accounts: dict[str, AuthAccount] = {}
    for sector_tenant_id, tenant_name, role, email in sector_fixtures:
        if not await db.get(Tenant, sector_tenant_id):
            db.add(Tenant(id=sector_tenant_id, name=tenant_name, state_location="Test Jurisdiction", status="ACTIVE"))
        account = await db.scalar(select(AuthAccount).where(AuthAccount.tenant_id == sector_tenant_id, AuthAccount.role == role, AuthAccount.identifier == email))
        if not account:
            account = AuthAccount(tenant_id=sector_tenant_id, role=role, identifier=email, email=email, first_name=tenant_name, last_name="Operator", password_hash=hash_password("Password123!"), is_active=True)
            db.add(account)
            await db.flush()
        sector_accounts[role] = account
    pharmacy_id, laboratory_id, payer_id, government_id = [item[0] for item in sector_fixtures]
    if not await db.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == pharmacy_id)):
        db.add(FacilityRegistry(tenant_id=pharmacy_id, facility_type="PHARMACY", country="NG", jurisdiction="NG-AK", status="ACTIVE", accepts_patients=False))
    if not await db.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == laboratory_id)):
        db.add(FacilityRegistry(tenant_id=laboratory_id, facility_type="LABORATORY", country="NG", jurisdiction="NG-AK", status="ACTIVE", accepts_patients=False))
    if not await db.scalar(select(PayerOrganization).where(PayerOrganization.tenant_id == payer_id)):
        db.add(PayerOrganization(tenant_id=payer_id, country_code="NG", payer_type="HMO", legal_name="ClinicalFlow Test HMO", status="ACTIVE"))
    authority = await db.scalar(select(GovernmentAuthority).where(GovernmentAuthority.tenant_id == government_id))
    if not authority:
        authority = GovernmentAuthority(tenant_id=government_id, country_code="NG", jurisdiction_code="NG-AK", authority_level="STATE", status="ACTIVE")
        db.add(authority)
        await db.flush()
    government_account = sector_accounts["government"]
    if not await db.scalar(select(GovernmentUserScope).where(GovernmentUserScope.user_id == government_account.id, GovernmentUserScope.jurisdiction_code == "NG-AK")):
        db.add(GovernmentUserScope(user_id=government_account.id, authority_id=authority.id, jurisdiction_code="NG-AK", geographic_level="STATE", status="ACTIVE"))
    await db.commit()
