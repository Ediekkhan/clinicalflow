from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_patient
from app.db.session import get_session
from app.middleware.rate_limit_config import RATE_LIMITS
from app.middleware.rate_limiter import check_rate_limit
from app.models.domain import Patient
from app.schemas.synaptiverse import TriageAnalyzeResponse
from app.schemas.ticket import TriageRequestSchema
from app.services.audit_service import AuditAction, write_audit_log
from app.services.triage_engine import analyze_triage


router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/analyze", response_model=TriageAnalyzeResponse)
async def analyze(
    payload: TriageRequestSchema,
    request: Request,
    current_patient: Patient = Depends(get_current_patient),
    session: AsyncSession = Depends(get_session),
):
    config = RATE_LIMITS["triage:analyze"]
    await check_rate_limit(
        key="triage:analyze",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=f"patient:{current_patient.id}",
    )
    try:
        result = await analyze_triage(
            session,
            current_patient.tenant_id,
            current_patient.id,
            payload.symptom_text,
            payload.latitude,
            payload.longitude,
        )
        await write_audit_log(
            db=session,
            action=AuditAction.TRIAGE_SUBMITTED,
            actor_id=str(current_patient.id),
            actor_type="PATIENT",
            tenant_id=str(current_patient.tenant_id),
            ip_address=request.client.host if request.client else "unknown",
            resource_type="TICKET",
            resource_id=str(result.ticket.id),
            metadata={"urgency": result.urgency, "condition": result.condition_name},
            user_agent=request.headers.get("user-agent"),
        )
        return result
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
