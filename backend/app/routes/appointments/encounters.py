from __future__ import annotations

from fastapi import APIRouter

from app.routes.clinical_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/encounters/{encounter_id}/notes", status_code=201)
async def add_clinical_note(
    encounter_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, CLINICIAN_ROLES)
    await verified_membership(session, account)
    encounter = await session.scalar(
        select(Encounter).where(
            Encounter.id == parse_uuid(encounter_id, "encounter_id"),
            Encounter.facility_id == account.tenant_id,
            Encounter.assigned_clinician_id == account.id,
        )
    )
    if not encounter:
        raise HTTPException(status_code=404, detail="Assigned encounter not found")
    payload = await request.json()
    body = str(payload.get("body") or "").strip()
    if len(body) < 3:
        raise HTTPException(status_code=422, detail="Clinical note is required")
    note = ClinicalNote(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        facility_id=encounter.facility_id,
        author_id=account.id,
        note_type=str(payload.get("note_type") or "PROGRESS").upper(),
        body=body,
    )
    session.add(note)
    await session.flush()
    await audit(
        session, request, account, "ClinicalNote", note.id, "CREATED", account.tenant_id
    )
    await session.commit()
    return {
        "id": str(note.id),
        "encounter_id": str(encounter.id),
        "status": note.status,
        "created_at": note.created_at,
    }
