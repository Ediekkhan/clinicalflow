from fastapi import APIRouter

from .dashboard import router as dashboard_router
from .departments import router as departments_router
from .settings import router as settings_router
from .staff import router as staff_router
from .waiting_room import router as waiting_room_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(departments_router)
router.include_router(settings_router)
router.include_router(staff_router)
router.include_router(waiting_room_router)

__all__ = ["router"]
