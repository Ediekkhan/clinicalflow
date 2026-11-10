from fastapi import APIRouter

from .login import router as login_router
from .profile import router as profile_router
from .sessions import router as sessions_router
from .workspaces import router as workspaces_router

router = APIRouter()
router.include_router(login_router)
router.include_router(profile_router)
router.include_router(sessions_router)
router.include_router(workspaces_router)

__all__ = ["router"]
