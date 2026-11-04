from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/auth/{role}/login", response_model=AuthSessionResponse)
async def login(
    role: str,
    payload: AuthLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    if role not in {
        "patient",
        "doctor",
        "specialist",
        "nurse",
        "department_coordinator",
        "hospital_admin",
        "pharmacy",
        "laboratory",
        "hmo",
        "government",
    }:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    identifier = (payload.phone or payload.email or "").strip().lower()
    if not identifier or not payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if role == "patient":
        account = await find_account(
            session, role, identifier, uuid.UUID(settings.operational_tenant_id)
        )
    else:
        account = await session.scalar(
            select(AuthAccount).where(
                AuthAccount.role == role,
                or_(
                    func.lower(AuthAccount.identifier) == identifier,
                    func.lower(AuthAccount.email) == identifier,
                ),
                AuthAccount.is_active.is_(True),
            )
        )
    # Supabase Auth is the password authority when configured. The linked
    # application account still supplies role, membership, and tenant scope.
    if settings.supabase_auth_enabled:
        supabase_id = await password_login(identifier, payload.password)
        if supabase_id:
            account = await session.scalar(
                select(AuthAccount).where(
                    AuthAccount.supabase_user_id == supabase_id,
                    AuthAccount.role == role,
                    AuthAccount.is_active.is_(True),
                )
            )
            # One-time safe migration: match the existing application account
            # by its normalized identifier, then persist the Auth user id.
            if not account:
                account = await session.scalar(
                    select(AuthAccount).where(
                        AuthAccount.role == role,
                        func.lower(AuthAccount.identifier) == identifier,
                        AuthAccount.is_active.is_(True),
                    )
                )
                if account and not account.supabase_user_id:
                    account.supabase_user_id = supabase_id
            if account:
                return await _login_account(account, request, response, session)
        if role == "hospital_admin":
            pending = await session.scalar(
                select(SignupApplication).where(
                    func.lower(SignupApplication.email) == identifier,
                    SignupApplication.application_type.in_(ORGANIZATION_SIGNUP_TYPES),
                    SignupApplication.status.in_(
                        {"PENDING_FACILITY_VERIFICATION", "PENDING_REVIEW", "PENDING"}
                    ),
                )
            )
            if pending:
                raise HTTPException(
                    status_code=403,
                    detail="Your hospital application is still pending facility approval. You can sign in after an administrator approves it.",
                )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = utc_now()
    if (
        account
        and account.locked_until
        and account.locked_until.replace(tzinfo=UTC) > now
    ):
        raise HTTPException(
            status_code=423, detail="Account is temporarily locked. Try again later."
        )
    if not account or not verify_password(payload.password, account.password_hash):
        if account:
            account.failed_login_attempts += 1
            if account.failed_login_attempts >= settings.auth_max_failed_attempts:
                account.locked_until = now + timedelta(
                    minutes=settings.auth_lockout_minutes
                )
            await session.commit()
        if role == "hospital_admin":
            pending = await session.scalar(
                select(SignupApplication).where(
                    func.lower(SignupApplication.email) == identifier,
                    SignupApplication.application_type.in_(ORGANIZATION_SIGNUP_TYPES),
                    SignupApplication.status.in_(
                        {"PENDING_FACILITY_VERIFICATION", "PENDING_REVIEW", "PENDING"}
                    ),
                )
            )
            if pending:
                raise HTTPException(
                    status_code=403,
                    detail="Your hospital application is still pending facility approval. You can sign in after an administrator approves it.",
                )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    account.failed_login_attempts = 0
    account.locked_until = None

    return await _login_account(account, request, response, session)


@router.post("/auth/staff/pin-login", response_model=AuthSessionResponse)
async def pin_login(
    payload: PinLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    if not settings.fixtures_enabled:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    identifier = f"uyo-family:{payload.role}"
    account = await find_account(
        session, payload.role, identifier, uuid.UUID(settings.operational_tenant_id)
    )
    if not account or not verify_password(payload.pin, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid role or PIN")
    return await _login_account(account, request, response, session)


@router.post("/auth/hospital/account-login", response_model=AuthSessionResponse)
async def hospital_login(
    payload: HospitalLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    if not settings.fixtures_enabled:
        raise HTTPException(status_code=404, detail="Authentication route not found")
    await enforce_rate_limit(request, "auth-login", settings.auth_rate_limit)
    identifier = f"{payload.hospital_code.strip().lower()}:{payload.role}"
    account = await find_account(
        session, payload.role, identifier, uuid.UUID(settings.operational_tenant_id)
    )
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid hospital credentials")
    return await _login_account(account, request, response, session)


@router.get("/auth/facility-admin/activation/{activation_token}")
async def inspect_facility_admin_activation(
    activation_token: str, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    activation = await session.scalar(
        select(FacilityAdminActivation).where(
            FacilityAdminActivation.token_hash == token_hash(activation_token)
        )
    )
    expires_at = (
        activation.expires_at.replace(tzinfo=UTC)
        if activation and activation.expires_at.tzinfo is None
        else activation.expires_at if activation else None
    )
    if (
        not activation
        or activation.status != "PENDING"
        or not expires_at
        or expires_at <= utc_now()
        or activation.revoked_at is not None
    ):
        raise HTTPException(
            status_code=400, detail="Activation link is invalid or expired"
        )
    account = await session.get(AuthAccount, activation.account_id)
    return {
        "valid": True,
        "email": account.email if account else None,
        "expires_at": activation.expires_at,
    }


@router.post("/auth/facility-admin/activate")
async def activate_facility_admin(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    payload = await request.json()
    raw_token = str(payload.get("token") or "")
    if (
        not raw_token
        or not payload.get("password")
        or not payload.get("mfa_setup")
        or not payload.get("terms_accepted")
    ):
        raise HTTPException(
            status_code=422,
            detail="Activation requires a token, new password, MFA setup, and terms acceptance",
        )
    activation = await session.scalar(
        select(FacilityAdminActivation)
        .where(FacilityAdminActivation.token_hash == token_hash(raw_token))
        .with_for_update()
    )
    expires_at = (
        activation.expires_at.replace(tzinfo=UTC)
        if activation and activation.expires_at.tzinfo is None
        else activation.expires_at if activation else None
    )
    if (
        not activation
        or activation.status != "PENDING"
        or not expires_at
        or expires_at <= utc_now()
        or activation.revoked_at is not None
    ):
        raise HTTPException(
            status_code=400, detail="Activation link is invalid or expired"
        )
    account = await session.get(
        AuthAccount, activation.account_id, with_for_update=True
    )
    if not account:
        raise HTTPException(status_code=404, detail="Activation account not found")
    membership = await session.scalar(
        select(StaffMembership)
        .where(
            StaffMembership.user_id == account.id,
            StaffMembership.hospital_id == account.tenant_id,
        )
        .with_for_update()
    )
    account.password_hash = hash_password(str(payload["password"]))
    account.is_active = True
    account.email_verified_at = utc_now()
    if membership:
        membership.is_active = True
        membership.employment_status = "ACTIVE"
        membership.verification_status = "VERIFIED"
    activation.status = "USED"
    activation.used_at = utc_now()
    activation.activated_at = activation.used_at
    case = await session.scalar(
        select(FacilityVerificationCase)
        .where(FacilityVerificationCase.id == activation.verification_case_id)
        .with_for_update()
    )
    if case:
        case.status = "SETUP_REQUIRED"
    await session.commit()
    return {"status": "SETUP_REQUIRED", "tenant_id": str(account.tenant_id)}
