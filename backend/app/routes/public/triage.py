from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/public/platform-stats")
async def public_platform_stats(
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    ticket_count = await session.scalar(
        select(func.count(Ticket.id)).where(Ticket.tenant_id == tenant_id)
    )
    active_count = await session.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.tenant_id == tenant_id,
            Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]),
        )
    )
    return {
        "patients_routed": int(ticket_count or 0),
        "active_visits": int(active_count or 0),
        "channels_connected": 3,
        "clinic_regions": 2,
    }


@router.post("/public/triage-preview")
async def public_triage_preview(request: Request) -> dict[str, Any]:
    await enforce_rate_limit(
        request, "public-triage-preview", settings.public_intake_rate_limit
    )
    payload = await request.json()
    symptom_text = str(payload.get("symptom_description") or "").strip()
    if len(symptom_text) < 3:
        raise HTTPException(
            status_code=422, detail="Describe the symptoms in a little more detail"
        )
    clinical_route = await request.app.state.knowledge_graph.route(symptom_text)
    urgency = clinical_route.derived_urgency
    timing = (
        "Seek emergency care now"
        if urgency == "CRITICAL"
        else (
            "See a clinician today"
            if urgency == "URGENT"
            else "Book the next available visit"
        )
    )
    return {
        "condition_name": clinical_route.condition_id.replace("_", " ").title(),
        "possible_illness": possible_illness_for_route(
            clinical_route.condition_id, clinical_route.symptom_ids
        ),
        "diagnosis_disclaimer": "This is not a diagnosis. A qualified clinician must confirm what illness you have.",
        "urgency": urgency,
        "specialty": clinical_route.target_specialty,
        "recommended_timing": timing,
        "severity": severity_for_urgency(urgency),
        "severity_label": severity_for_urgency(urgency).title(),
        "matched_symptoms": clinical_route.symptom_ids,
        "disclaimer": "This preview is informational and does not replace assessment by a qualified clinician.",
    }
