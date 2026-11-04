from fastapi import APIRouter

from .content import router as content_router
from .triage import router as triage_router

router = APIRouter()
router.include_router(content_router)
router.include_router(triage_router)

__all__ = ["router"]
