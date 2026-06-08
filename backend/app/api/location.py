from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.synaptiverse import ClinicMatch
from app.services.location_service import nearby_clinics


router = APIRouter(prefix="/clinics", tags=["location"])


@router.get("/nearby", response_model=list[ClinicMatch])
async def clinics_nearby(
    lat: float = Query(...),
    lng: float = Query(...),
    specialty: str = "General Practitioner",
    urgency: str = "ROUTINE",
    session: AsyncSession = Depends(get_session),
):
    return await nearby_clinics(session, lat, lng, specialty, urgency)

