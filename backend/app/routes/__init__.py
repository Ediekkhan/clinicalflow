"""ClinicalFlow API route composition."""

from typing import Any

from .helpers import TriageConnectionManager, secrets, triage_manager
from .appointments import router as appointments_router
from .auth import router as auth_router
from .billing import router as billing_router
from .government import router as government_router
from .hospitals import router as hospitals_router
from .insurance import router as insurance_router
from .laboratory import router as laboratory_router
from .notifications import router as notifications_router
from .patients import router as patients_router
from .pharmacy import router as pharmacy_router
from .platform import router as platform_router
from .public import router as public_router
from .referrals import router as referrals_router
from .signup import router as signup_router
from .specialists import router as specialists_router
from .terminology import router as terminology_router
from .tickets import router as tickets_router


def register_routes(app: Any) -> None:
    app.include_router(auth_router)
    app.include_router(signup_router)
    app.include_router(hospitals_router)
    app.include_router(tickets_router)
    app.include_router(appointments_router)
    app.include_router(billing_router)
    app.include_router(public_router)
    app.include_router(referrals_router)
    app.include_router(laboratory_router)
    app.include_router(pharmacy_router)
    app.include_router(insurance_router)
    app.include_router(government_router)
    app.include_router(terminology_router)
    app.include_router(patients_router)
    app.include_router(specialists_router)
    app.include_router(notifications_router)
    # The platform router contains deliberately generic operational portal
    # paths, so it must remain last to avoid shadowing concrete domains.
    app.include_router(platform_router)


__all__ = [
    "TriageConnectionManager",
    "register_routes",
    "secrets",
    "triage_manager",
]
