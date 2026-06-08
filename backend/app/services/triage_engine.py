import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.graph.neo4j_client import ConditionRoute, route_symptoms
from app.models.domain import Appointment, Patient, Specialist, Ticket
from app.schemas.synaptiverse import AppointmentSlotSummary, ClinicMatch, TriageAnalyzeResponse, SynTicketRead
from app.services.lexicon import extract_symptoms
from app.services.location_service import nearby_clinics
from app.services.notification_service import create_notification
from app.services.realtime import connection_manager
from app.services.tickets import generate_ticket_number


FALLBACK_NAME_BY_ID = {
    "S001": "chest pain",
    "S002": "shortness of breath",
    "S003": "fever",
    "S004": "severe headache",
}


async def extract_with_anthropic(symptom_text: str) -> list[str]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        extracted = await extract_symptoms(symptom_text)
        mapped = {
            "chest_pain": "S001",
            "short_breath": "S002",
            "fever": "S003",
            "headache": "S004",
            "pregnancy_pain": "S018",
            "bleeding": "S020",
        }
        return [mapped[item] for item in extracted.symptom_ids if item in mapped] or ["S003"]

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 400,
                "system": (
                    "You are a Nigerian clinical triage assistant. Extract a JSON list of "
                    "standardized symptom IDs from the patient's description. Return ONLY JSON: "
                    "{symptom_ids: [...], raw_symptoms: [...], language_detected: 'english'|'pidgin'}"
                ),
                "messages": [{"role": "user", "content": symptom_text}],
            },
        )
    response.raise_for_status()
    content = response.json()["content"][0]["text"]
    return json.loads(content)["symptom_ids"]


async def condition_route(symptom_ids: list[str]) -> ConditionRoute:
    try:
        route = await route_symptoms(symptom_ids)
        if route:
            return route
    except Exception:
        pass
    if "S001" in symptom_ids or "S002" in symptom_ids:
        return ConditionRoute("Cardiologist", "CRITICAL", "C001", "Acute Myocardial Infarction")
    if "S018" in symptom_ids:
        return ConditionRoute("Obstetrician", "URGENT", "C012", "Preeclampsia")
    return ConditionRoute("General Practitioner", "ROUTINE", "C003", "Malaria")


async def analyze_triage(
    session: AsyncSession,
    tenant_id: UUID,
    patient_id: UUID,
    symptom_text: str,
    latitude: float | None,
    longitude: float | None,
) -> TriageAnalyzeResponse:
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise LookupError("Patient not found.")

    symptom_ids = await extract_with_anthropic(symptom_text)
    route = await condition_route(symptom_ids)
    lat = latitude if latitude is not None else float(patient.latitude or 5.0377)
    lng = longitude if longitude is not None else float(patient.longitude or 7.9128)
    clinics = await nearby_clinics(session, lat, lng, route.specialty, route.urgency)
    nearest = clinics[0] if clinics else ClinicMatch(
        clinic_id=tenant_id,
        clinic_name="Uyo Family Clinic",
        address="112 Wellington Bassey Way, Uyo",
        distance_km=2.4,
        available_slots=4,
        specialist_id=None,
        specialist_name=None,
    )

    specialist = None
    if nearest.specialist_id:
        specialist = await session.get(Specialist, nearest.specialist_id)
    if specialist is None:
        specialist = (
            await session.scalars(
                select(Specialist)
                .where(Specialist.tenant_id == tenant_id)
                .where(Specialist.is_available.is_(True))
                .limit(1)
            )
        ).first()

    slot_start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
    slot_end = slot_start + timedelta(hours=1)
    ticket = Ticket(
        tenant_id=tenant_id,
        patient_id=patient_id,
        ticket_number=await generate_ticket_number(session),
        customer_phone=patient.phone,
        account_group_phone=patient.phone,
        channel="WEB",
        symptom_description=symptom_text,
        raw_intake_text=symptom_text,
        extracted_symptom_ids=symptom_ids,
        extracted_symptoms=",".join(symptom_ids),
        matched_condition_id=route.condition_id,
        matched_condition_name=route.condition_name,
        assigned_specialty=route.specialty,
        urgency_level=route.urgency,
        assigned_specialist_id=specialist.id if specialist else None,
        assigned_clinic_id=nearest.clinic_id,
        appointment_slot=slot_start,
        queue_status="QUEUED",
    )
    session.add(ticket)
    await session.flush()

    appointment = Appointment(
        tenant_id=tenant_id,
        ticket_id=ticket.id,
        patient_id=patient_id,
        specialist_id=specialist.id if specialist else None,
        clinic_id=nearest.clinic_id,
        slot_start=slot_start,
        slot_end=slot_end,
        status="BOOKED",
        channel_origin="WEB",
    )
    session.add(appointment)
    await session.flush()

    if specialist:
        await create_notification(
            session,
            tenant_id,
            "SPECIALIST",
            specialist.id,
            "New triage assignment",
            f"{patient.full_name} was routed for {route.condition_name} ({route.urgency}).",
            ticket.id,
        )

    ticket_payload = SynTicketRead.model_validate(ticket).model_dump(mode="json")
    if specialist:
        await connection_manager.broadcast_specialist(
            specialist.id,
            {"type": "ticket.created", "payload": ticket_payload},
        )
    await connection_manager.broadcast_queue(
        patient.card_number,
        {"type": "queue.updated", "payload": ticket_payload},
    )

    severity = {
        "CRITICAL": "This appears urgent and may need emergency care. Please proceed immediately.",
        "URGENT": "You should be reviewed soon by the recommended specialist.",
        "ROUTINE": "Your symptoms look stable enough for a routine consultation, but you should come in today.",
    }[route.urgency]

    return TriageAnalyzeResponse(
        ticket=SynTicketRead.model_validate(ticket),
        condition_name=route.condition_name,
        urgency=route.urgency,  # type: ignore[arg-type]
        specialty=route.specialty,
        nearest_clinic=nearest,
        appointment_slot=AppointmentSlotSummary(
            slot_start=slot_start,
            slot_end=slot_end,
            specialist_name=specialist.full_name if specialist else nearest.specialist_name or "Available clinician",
            specialty=route.specialty,
        ),
        severity_message=severity,
    )
