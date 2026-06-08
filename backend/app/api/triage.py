from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_tenant_id
from app.db.session import get_session
from app.schemas.synaptiverse import TriageAnalyzeRequest, TriageAnalyzeResponse
from app.services.triage_engine import analyze_triage


router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/analyze", response_model=TriageAnalyzeResponse)
async def analyze(
    payload: TriageAnalyzeRequest,
    tenant_id=Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await analyze_triage(
            session,
            tenant_id,
            payload.patient_id,
            payload.symptom_text,
            payload.latitude,
            payload.longitude,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

