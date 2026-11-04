from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post(
    "/signup/patient", response_model=SignupApplicationResponse, status_code=201
)
async def signup_patient(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("patient", payload, request, response, session)


@router.post(
    "/signup/specialist", response_model=SignupApplicationResponse, status_code=201
)
async def signup_specialist(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("specialist", payload, request, response, session)


@router.post(
    "/signup/hospital", response_model=SignupApplicationResponse, status_code=201
)
async def signup_hospital(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("hospital", payload, request, response, session)


@router.post(
    "/signup/clinic", response_model=SignupApplicationResponse, status_code=201
)
async def signup_clinic(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("clinic", payload, request, response, session)


@router.post("/signup/nurse", response_model=SignupApplicationResponse, status_code=201)
async def signup_nurse(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("nurse", payload, request, response, session)


@router.post(
    "/signup/pharmacy", response_model=SignupApplicationResponse, status_code=201
)
async def signup_pharmacy(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("pharmacy", payload, request, response, session)


@router.post(
    "/signup/laboratory", response_model=SignupApplicationResponse, status_code=201
)
async def signup_laboratory(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("laboratory", payload, request, response, session)


@router.post("/signup/hmo", response_model=SignupApplicationResponse, status_code=201)
async def signup_hmo(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("hmo", payload, request, response, session)


@router.post(
    "/signup/government", response_model=SignupApplicationResponse, status_code=201
)
async def signup_government(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("government", payload, request, response, session)


@router.post(
    "/signup/platform-admin", response_model=SignupApplicationResponse, status_code=201
)
async def signup_platform_admin(
    payload: SignupApplicationCreate,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> SignupApplicationResponse:
    return await _create_signup("platform-admin", payload, request, response, session)
