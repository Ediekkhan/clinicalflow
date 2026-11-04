from __future__ import annotations

from fastapi import APIRouter

from app.routes.sector_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/platform/support-access", status_code=201)
async def request_support_access(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    hours = max(1, min(int(payload.get("hours") or 1), 8))
    if len(reason) < 10:
        raise HTTPException(
            status_code=422, detail="A specific support reason is required"
        )
    row = SupportAccessRequest(
        requester_id=account.id,
        facility_id=parse_uuid(payload.get("facility_id"), "facility_id"),
        reason=reason,
        sensitive_access=bool(payload.get("sensitive_access", True)),
        expires_at=utc_now() + timedelta(hours=hours),
    )
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status, "expires_at": row.expires_at}


@router.post("/platform/support-access/{request_id}/approvals", status_code=201)
async def approve_support_access(
    request_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    row = await session.scalar(
        select(SupportAccessRequest)
        .where(SupportAccessRequest.id == parse_uuid(request_id, "request_id"))
        .with_for_update()
    )
    if (
        not row
        or row.status not in {"PENDING", "APPROVED"}
        or is_expired(row.expires_at)
    ):
        raise HTTPException(
            status_code=409, detail="Support access request is not open"
        )
    await require_staff_workspace(
        session,
        account,
        hospital_id=row.facility_id,
        roles={"hospital_admin", "department_coordinator"},
    )
    payload = await request.json()
    decision, reason = (
        str(payload.get("decision") or "").upper(),
        str(payload.get("reason") or "").strip(),
    )
    if decision not in {"APPROVED", "DENIED"} or len(reason) < 3:
        raise HTTPException(
            status_code=422, detail="Approval decision and reason are required"
        )
    session.add(
        SupportAccessApproval(
            request_id=row.id, approver_id=account.id, decision=decision, reason=reason
        )
    )
    await session.flush()
    approvals = await session.scalar(
        select(func.count())
        .select_from(SupportAccessApproval)
        .where(
            SupportAccessApproval.request_id == row.id,
            SupportAccessApproval.decision == "APPROVED",
        )
    )
    if decision == "DENIED":
        row.status = "DENIED"
    elif approvals >= (2 if row.sensitive_access else 1):
        row.status, row.activated_at = "ACTIVE", utc_now()
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "approvals": approvals,
        "expires_at": row.expires_at,
    }
