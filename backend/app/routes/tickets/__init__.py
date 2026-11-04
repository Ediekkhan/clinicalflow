from fastapi import APIRouter

from .intake import router as intake_router
from .queue import router as queue_router
from .routing import router as routing_router

router = APIRouter()
router.include_router(intake_router)
router.include_router(queue_router)
router.include_router(routing_router)

__all__ = ["router"]
