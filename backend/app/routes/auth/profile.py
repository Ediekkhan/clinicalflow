from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/auth/{role}/me", response_model=AuthProfileResponse)
async def get_current_profile(role: str, request: Request) -> AuthProfileResponse:
    async with request.app.state.session_factory() as session:
        authorization = request.headers.get("authorization", "")
        token = request.cookies.get(ACCESS_COOKIE) or (
            authorization[7:].strip()
            if authorization.lower().startswith("bearer ")
            else None
        )
        authenticated = (
            await account_for_access_token(session, token) if token else None
        )
        if not authenticated:
            raise HTTPException(status_code=401, detail="Authentication required")
        if authenticated[0].role != role:
            raise HTTPException(
                status_code=403,
                detail="Authenticated account is not authorized for this role",
            )
        return _build_profile(authenticated[0])
