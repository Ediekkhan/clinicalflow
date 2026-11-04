from fastapi import APIRouter

from .encounters import router as encounters_router
from .hospitals import router as hospitals_router
from .routes import router as routes_router

router = APIRouter()
router.include_router(encounters_router)
router.include_router(hospitals_router)
router.include_router(routes_router)

__all__ = ["router"]
