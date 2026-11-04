from fastapi import APIRouter

from .applications import router as applications_router
from .invitations import router as invitations_router
from .verification import router as verification_router

router = APIRouter()
router.include_router(applications_router)
router.include_router(invitations_router)
router.include_router(verification_router)

__all__ = ["router"]
