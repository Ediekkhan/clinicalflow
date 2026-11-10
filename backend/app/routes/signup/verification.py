from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/signup/verify-phone", response_model=SignupApplicationResponse)
async def verify_signup_phone(
    payload: SignupVerificationRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _verify_patient(payload, response, session, "PHONE_OTP")


@router.post("/signup/verify-email", response_model=SignupApplicationResponse)
async def verify_signup_email(
    payload: SignupVerificationRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _verify_patient(payload, response, session, "EMAIL_OTP")


@router.get("/signup/status/{application_id}", response_model=SignupApplicationResponse)
async def signup_status(
    application_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> SignupApplicationResponse:
    application = await session.get(SignupApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Signup application not found")
    return SignupApplicationResponse(
        id=application.id,
        reference=application.reference,
        application_type=application.application_type,
        onboarding_type=application.onboarding_type,
        status=application.status,
        submitted_at=application.submitted_at,
        login_path=SIGNUP_LOGIN_PATHS[application.application_type],
        dashboard_path=(
            SIGNUP_DASHBOARD_PATHS[application.application_type]
            if application.status == "ACTIVE"
            else None
        ),
    )
