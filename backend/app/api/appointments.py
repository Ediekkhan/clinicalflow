from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_tenant_id
from app.db.session import get_session
from app.middleware.rate_limit_config import RATE_LIMITS
from app.middleware.rate_limiter import check_rate_limit, get_rate_limit_identifier
from app.schemas.domain import AppointmentCreate, AppointmentRead, ProviderSlotRead
from app.services.appointments import create_appointment, list_open_slots, lock_slot


router = APIRouter(prefix="/appointments", tags=["appointments"])


class SlotLockRequest(BaseModel):
    is_locked: bool
    reason: str | None = None


@router.get("/slots", response_model=list[ProviderSlotRead])
async def open_slots(
    starts_after: datetime | None = Query(default=None),
    specialty: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ProviderSlotRead]:
    slots = await list_open_slots(session, starts_after=starts_after, specialty=specialty)
    return [ProviderSlotRead.model_validate(slot) for slot in slots]


@router.post("", response_model=dict[str, object])
async def book_appointment(
    payload: AppointmentCreate,
    request: Request,
    tenant_id: UUID = Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    config = RATE_LIMITS["appointments:create"]
    await check_rate_limit(
        key="appointments:create",
        limit=config["requests"],
        window_seconds=config["window_seconds"],
        identifier=await get_rate_limit_identifier(request),
    )
    try:
        appointment, outbound_message = await create_appointment(
            session,
            tenant_id,
            payload.ticket_id,
            payload.provider_slot_id,
            payload.channel_origin,
        )
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "appointment": AppointmentRead.model_validate(appointment).model_dump(mode="json"),
        "outbound_message_preview": outbound_message,
    }


@router.patch("/slots/{slot_id}/lock", response_model=ProviderSlotRead)
async def set_slot_lock(
    slot_id: UUID,
    payload: SlotLockRequest,
    tenant_id: UUID = Depends(current_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> ProviderSlotRead:
    try:
        slot = await lock_slot(session, tenant_id, slot_id, payload.is_locked, payload.reason)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProviderSlotRead.model_validate(slot)
