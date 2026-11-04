from fastapi import APIRouter

from .documents import router as documents_router
from .enterprise import router as enterprise_router
from .infrastructure import router as infrastructure_router
from .operations import router as operations_router
from .support import router as support_router
from .verifications import router as verifications_router

router = APIRouter()
router.include_router(documents_router)
router.include_router(enterprise_router)
router.include_router(infrastructure_router)
router.include_router(support_router)
router.include_router(verifications_router)
# Generic /{entity}/{resource} routes must be registered after every concrete
# platform endpoint.
router.include_router(operations_router)

__all__ = ["router"]
