from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/auth/refresh", response_model=AuthRefreshResponse)
async def refresh_auth(
    request: Request, response: Response, session: AsyncSession = Depends(get_db)
) -> AuthRefreshResponse:
    token = request.cookies.get(REFRESH_COOKIE)
    authenticated = await session_for_refresh_token(session, token) if token else None
    if not authenticated:
        raise HTTPException(status_code=401, detail="Refresh session expired")
    account, previous = authenticated
    previous.revoked_at = utc_now()
    previous.revoked_reason = "REFRESH_ROTATED"
    issued = await create_session(
        session,
        account,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    _set_session_cookies(response, issued.access_token, issued.refresh_token)
    return AuthRefreshResponse(access_expires_at=issued.session.access_expires_at)


@router.post("/auth/logout", status_code=204)
async def logout_auth(
    request: Request, response: Response, session: AsyncSession = Depends(get_db)
) -> Response:
    token = request.cookies.get(REFRESH_COOKIE)
    authenticated = await session_for_refresh_token(session, token) if token else None
    if authenticated:
        authenticated[1].revoked_at = utc_now()
        authenticated[1].revoked_reason = "LOGOUT"
        await session.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    _delete_legacy_auth_cookies(response)
    response.status_code = 204
    return response


@router.post("/auth/logout-all", status_code=204)
async def logout_all_auth(
    request: Request, response: Response, session: AsyncSession = Depends(get_db)
) -> Response:
    account = await require_account(request, session)
    now = utc_now()
    sessions = list(
        (
            await session.execute(
                select(AuthSession).where(
                    AuthSession.account_id == account.id,
                    AuthSession.revoked_at.is_(None),
                )
            )
        ).scalars()
    )
    for auth_session in sessions:
        auth_session.revoked_at = now
        auth_session.revoked_reason = "LOGOUT_ALL"
    await session.commit()
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")
    _delete_legacy_auth_cookies(response)
    response.status_code = 204
    return response
