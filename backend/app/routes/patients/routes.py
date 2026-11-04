from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/patient/consents")
async def patient_consents(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    patient = await ensure_patient_registry(session, account)
    rows = list(
        (
            await session.execute(
                select(PatientConsentDirective)
                .where(PatientConsentDirective.patient_id == patient.id)
                .order_by(PatientConsentDirective.purpose)
            )
        )
        .scalars()
        .all()
    )
    await session.commit()
    return {
        "items": [
            {
                "id": str(item.id),
                "purpose": item.purpose,
                "grantee_type": item.grantee_type,
                "grantee_id": str(item.grantee_id) if item.grantee_id else None,
                "status": item.status,
                "data_categories": (
                    json.loads(item.data_categories_json)
                    if item.data_categories_json
                    else []
                ),
                "policy_version": item.policy_version,
                "granted_at": item.granted_at,
                "revoked_at": item.revoked_at,
            }
            for item in rows
        ]
    }


@router.patch("/patient/consents/{purpose}")
async def update_patient_consent(
    purpose: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    payload = await request.json()
    status = str(payload.get("status") or "").upper()
    if status not in {"ACTIVE", "WITHDRAWN"}:
        raise HTTPException(
            status_code=422, detail="Consent status must be ACTIVE or WITHDRAWN"
        )
    patient = await ensure_patient_registry(session, account)
    directive = await session.scalar(
        select(PatientConsentDirective)
        .where(
            PatientConsentDirective.patient_id == patient.id,
            PatientConsentDirective.purpose == purpose.upper(),
            PatientConsentDirective.grantee_type == "CARE_TEAM",
            PatientConsentDirective.grantee_id.is_(None),
        )
        .with_for_update()
    )
    if not directive:
        directive = PatientConsentDirective(
            patient_id=patient.id,
            purpose=purpose.upper(),
            grantee_type="CARE_TEAM",
            status=status,
            policy_version="2026-07",
        )
        session.add(directive)
    directive.status = status
    directive.data_categories_json = json.dumps(payload.get("data_categories") or [])
    directive.revoked_at = utc_now() if status == "WITHDRAWN" else None
    if status == "ACTIVE":
        directive.granted_at = utc_now()
    await session.flush()
    session.add(
        ProvenanceRecord(
            tenant_id=account.tenant_id,
            resource_type="PatientConsentDirective",
            resource_id=directive.id,
            action=status,
            actor_account_id=account.id,
            source="PATIENT_PORTAL",
        )
    )
    await session.commit()
    return {
        "id": str(directive.id),
        "purpose": directive.purpose,
        "status": directive.status,
    }


@router.get("/patient/health-card")
async def patient_health_card(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    patient = await ensure_patient_registry(session, account)
    tenant = await session.get(Tenant, account.tenant_id)
    if tenant:
        await ensure_facility_registry(session, tenant)
    credential, raw_token = await issue_health_card_credential(
        session, account, patient
    )
    await session.commit()
    return {
        "card_number": account.card_number,
        "internal_patient_id": patient.internal_identifier,
        "issuer": tenant.name if tenant else None,
        "issued_at": credential.issued_at,
        "expires_at": credential.expires_at,
        "emergency_access_enabled": credential.emergency_access_enabled,
        "qr_payload": f"clinicalflow://health-card/{raw_token}",
    }


@router.post("/health-card/lookup")
async def health_card_lookup(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"doctor", "specialist", "nurse"})
    payload = await request.json()
    raw_token = (
        str(payload.get("token") or "")
        .removeprefix("clinicalflow://health-card/")
        .strip()
    )
    if not raw_token:
        raise HTTPException(
            status_code=422, detail="A secure health-card token is required"
        )
    credential = await session.scalar(
        select(HealthCardCredential)
        .where(
            HealthCardCredential.token_hash == token_hash(raw_token),
            HealthCardCredential.status == "ACTIVE",
        )
        .limit(1)
    )
    if not credential or (
        credential.expires_at and credential.expires_at.replace(tzinfo=UTC) <= utc_now()
    ):
        raise HTTPException(
            status_code=404, detail="Health-card credential is invalid or expired"
        )
    patient = await session.get(PatientRegistry, credential.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient registry record not found")
    membership = await require_staff_workspace(
        session,
        account,
        hospital_id=credential.issuer_facility_id,
        roles={"doctor", "specialist", "nurse"},
    )
    consent = await session.scalar(
        select(PatientConsentDirective)
        .where(
            PatientConsentDirective.patient_id == patient.id,
            PatientConsentDirective.purpose == "CARE_DELIVERY",
            PatientConsentDirective.status == "ACTIVE",
        )
        .limit(1)
    )
    if not consent:
        session.add(
            ProvenanceRecord(
                tenant_id=membership.hospital_id,
                resource_type="HealthCardCredential",
                resource_id=credential.id,
                action="ACCESS_DENIED_CONSENT",
                actor_account_id=account.id,
                source="CLINICIAN_PORTAL",
            )
        )
        await session.commit()
        raise HTTPException(
            status_code=403, detail="Patient consent does not permit health-card lookup"
        )
    session.add(
        ProvenanceRecord(
            tenant_id=membership.hospital_id,
            resource_type="HealthCardCredential",
            resource_id=credential.id,
            action="LOOKED_UP",
            actor_account_id=account.id,
            source="CLINICIAN_PORTAL",
        )
    )
    await session.commit()
    return {
        "patient_id": str(patient.id),
        "internal_patient_id": patient.internal_identifier,
        "name": f"{patient.first_name} {patient.last_name}".strip(),
        "date_of_birth": patient.date_of_birth,
        "card_number": credential.card_number.rsplit("-", 1)[0],
        "issuer_facility_id": str(credential.issuer_facility_id),
        "emergency_access_enabled": credential.emergency_access_enabled,
    }


@router.patch("/patient/profile", response_model=AuthProfileResponse)
async def update_patient_profile(
    payload: PatientProfileUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> AuthProfileResponse:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    updates = payload.model_dump(exclude_unset=True)
    full_name = updates.pop("full_name", None)
    if full_name:
        name_parts = full_name.strip().split(maxsplit=1)
        account.first_name = name_parts[0]
        account.last_name = name_parts[1] if len(name_parts) > 1 else ""
    for field, value in updates.items():
        setattr(account, field, value.strip() if isinstance(value, str) else value)
    if "phone" in updates and updates["phone"]:
        account.identifier = updates["phone"]
    await session.commit()
    return _build_profile(account)


@router.patch("/patient/card-details", response_model=AuthProfileResponse)
async def update_patient_card(
    payload: PatientCardUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> AuthProfileResponse:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value.strip() if isinstance(value, str) else value)
    await session.commit()
    return _build_profile(account)


@router.get("/patient/history")
async def patient_history(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_account(request, session)
    if account.role != "patient" or not account.phone:
        raise HTTPException(status_code=403, detail="Patient access required")
    tickets = (
        (
            await session.execute(
                select(Ticket)
                .where(Ticket.customer_phone == account.phone)
                .order_by(Ticket.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    appointment_rows = (
        await session.execute(
            select(Appointment, ProviderSlot, Provider)
            .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id)
            .join(Provider, Provider.id == ProviderSlot.provider_id)
            .where(
                Appointment.tenant_id == account.tenant_id,
                Appointment.customer_phone == account.phone,
            )
            .order_by(Appointment.created_at.desc())
        )
    ).all()
    events = [
        {
            "id": str(ticket.id),
            "type": "TRIAGE",
            "title": f"Triage ticket {ticket.ticket_number}",
            "summary": ticket.raw_intake_text,
            "status": ticket.urgency_level,
            "created_at": ticket.created_at,
            "tone": "rose" if ticket.urgency_level == "CRITICAL" else "sky",
        }
        for ticket in tickets
    ]
    events.extend(
        {
            "id": str(appointment.id),
            "type": "APPOINTMENT",
            "title": f"Appointment with {provider.full_name}",
            "provider_name": provider.full_name,
            "facility_name": provider.room_label,
            "status": appointment.status,
            "created_at": appointment.created_at,
            "tone": "violet",
        }
        for appointment, _slot, provider in appointment_rows
    )
    report_rows = (
        await session.execute(
            select(DiagnosticReport, LaboratoryOrder, Tenant)
            .join(LaboratoryOrder, LaboratoryOrder.id == DiagnosticReport.order_id)
            .join(Tenant, Tenant.id == LaboratoryOrder.laboratory_id)
            .where(
                LaboratoryOrder.patient_id == account.id,
                DiagnosticReport.released_to_patient_at.is_not(None),
            )
            .order_by(DiagnosticReport.released_to_patient_at.desc())
        )
    ).all()
    events.extend(
        {
            "id": str(report.id),
            "type": "LAB_RESULT",
            "title": "Laboratory report",
            "summary": report.conclusion,
            "facility_name": laboratory.name,
            "status": report.status,
            "created_at": report.released_to_patient_at,
            "tone": "success",
        }
        for report, _order, laboratory in report_rows
    )
    return sorted(events, key=lambda event: event["created_at"], reverse=True)


@router.get("/patient/dashboard")
async def patient_dashboard(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient" or not account.phone:
        raise HTTPException(status_code=403, detail="Patient access required")
    tickets = (
        (
            await session.execute(
                select(Ticket)
                .where(Ticket.customer_phone == account.phone)
                .order_by(Ticket.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    next_slot = (
        await session.execute(
            select(ProviderSlot)
            .join(Appointment, Appointment.slot_id == ProviderSlot.id)
            .where(
                Appointment.tenant_id == account.tenant_id,
                Appointment.customer_phone == account.phone,
                Appointment.status == "BOOKED",
                ProviderSlot.starts_at >= utc_now(),
            )
            .order_by(ProviderSlot.starts_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    active = [ticket for ticket in tickets if ticket.queue_status != "RESOLVED"]
    queue = await patient_queue(request, session)
    return {
        "stats": {
            "active_tickets": len(active),
            "next_appointment": (
                next_slot.starts_at.isoformat() if next_slot else "None scheduled"
            ),
            "queue_position": queue["queue_position"] if queue else "—",
            "health_card_status": "Active" if account.card_number else "Not issued",
        },
        "activity": [
            {
                "id": str(ticket.id),
                "title": f"{ticket.ticket_number} · {ticket.queue_status.replace('_', ' ').title()}",
                "created_at": ticket.created_at.isoformat(),
            }
            for ticket in tickets[:5]
        ],
        "health_tip": {
            "title": "Prepare for your visit",
            "body": "Keep your ticket number available and bring a list of current medications.",
        },
    }


@router.get("/patient/queue")
async def patient_queue(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any] | None:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    result = await session.execute(
        select(Ticket)
        .where(
            Ticket.customer_phone == account.phone,
            Ticket.queue_status.in_(["QUEUED", "BEING_SEEN"]),
        )
        .order_by(Ticket.created_at.asc())
    )
    active_tickets = list(result.scalars().all())
    patient_ticket = next(
        (ticket for ticket in active_tickets if ticket.queue_status == "BEING_SEEN"),
        active_tickets[0] if active_tickets else None,
    )
    if not patient_ticket:
        return None
    destination_id = ticket_destination_id(patient_ticket)
    ahead_result = await session.execute(
        select(Ticket.id).where(
            ticket_destination_queue(destination_id),
            Ticket.queue_status == "QUEUED",
            Ticket.created_at < patient_ticket.created_at,
        )
    )
    return {
        "ticket_number": patient_ticket.ticket_number,
        "queue_position": (
            len(ahead_result.scalars().all()) + 1
            if patient_ticket.queue_status == "QUEUED"
            else 0
        ),
        "queue_status": patient_ticket.queue_status,
    }


@router.post("/patient/triage")
async def patient_triage(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role != "patient":
        raise HTTPException(status_code=403, detail="Patient access required")
    payload = await request.json()
    symptom_text = str(payload.get("symptom_description") or "").strip()
    if len(symptom_text) < 3:
        raise HTTPException(
            status_code=422, detail="Describe the symptoms in a little more detail"
        )
    latitude, longitude = patient_coordinates_from_payload(payload)
    country_code = (
        str(payload.get("current_country_code") or payload.get("country_code") or "")
        .strip()
        .upper()
    )
    if len(country_code) != 2 or not country_code.isalpha():
        raise HTTPException(
            status_code=422,
            detail="Current country code is required for safe local routing",
        )
    max_distance = payload.get("service_radius_km")
    try:
        max_distance = float(max_distance) if max_distance not in (None, "") else None
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail="Service radius must be a valid number of kilometres",
        )
    preferred_id = None
    if payload.get("preferred_facility_id"):
        try:
            preferred_id = uuid.UUID(str(payload["preferred_facility_id"]))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Preferred facility identifier is invalid"
            )
    clinical_route = await request.app.state.knowledge_graph.route(symptom_text)
    policy_radius = radius_for_urgency(
        country_code, str(clinical_route.derived_urgency)
    )
    if policy_radius is None:
        raise HTTPException(
            status_code=422,
            detail="This country is not enabled for automated routing yet",
        )
    max_distance = (
        min(max_distance, policy_radius) if max_distance is not None else policy_radius
    )
    candidates = await rank_eligible_facilities(
        session,
        latitude,
        longitude,
        clinical_route,
        preferred_facility_id=preferred_id,
        patient_country_code=country_code,
        max_distance_km=max_distance,
    )
    route = await select_nearest_eligible_hospital(
        session,
        latitude,
        longitude,
        clinical_route,
        preferred_facility_id=preferred_id,
        patient_country_code=country_code,
        max_distance_km=max_distance,
    )
    ticket = await persist_ticket(
        TicketCreate(
            customer_phone=account.phone or "",
            raw_intake_text=symptom_text,
            channel="WEB",
        ),
        request,
        session,
        clinical_route,
        account.tenant_id,
        route.tenant.id if route else None,
        latitude,
        longitude,
        route.distance_km if route else None,
        route_attempted=True,
    )
    if not route:
        reason = "No registered facility met the clinical capability, staffing, emergency, capacity, and intake requirements"
        await persist_routing_decision(
            session,
            ticket,
            clinical_route,
            candidates,
            None,
            preferred_id,
            reason,
            patient_country_code=country_code,
        )
        policy = country_policy(country_code)
        emergency_message = (
            f"For emergencies, contact local emergency services at {policy.emergency_number}."
            if policy
            else "Contact your local emergency services immediately if this is an emergency."
        )
        message = f"No eligible ClinicalFlow hospital is currently available in your country. {emergency_message if clinical_route.derived_urgency == 'CRITICAL' else 'You can request telemedicine or local-directory assistance.'}"
        raise HTTPException(
            status_code=503,
            detail={
                "code": "NO_LOCAL_FACILITY",
                "message": message,
                "country_code": country_code,
                "cross_border": False,
                "ticket_id": str(ticket.id),
                "urgency": clinical_route.derived_urgency,
            },
        )
    await persist_routing_decision(
        session,
        ticket,
        clinical_route,
        candidates,
        route.tenant.id,
        preferred_id,
        route.match_basis,
        patient_country_code=country_code,
        route_distance_km=route.distance_km,
    )
    slot_payload = None
    if route.slot and route.provider:
        slot_payload = {
            "slot_id": str(route.slot.id),
            "slot_start": route.slot.starts_at.isoformat(),
            "slot_end": route.slot.ends_at.isoformat(),
            "specialist_name": route.provider.full_name,
            "specialty": route.provider.specialty,
            "room_label": route.provider.room_label,
        }
    alternatives = sorted(
        (
            item
            for item in candidates
            if item.eligible and item.tenant.id != route.tenant.id
        ),
        key=lambda item: item.rank or 999999,
    )[:3]
    selected_candidate = next(
        item for item in candidates if item.tenant.id == route.tenant.id
    )
    return {
        "condition_name": clinical_route.condition_id.replace("_", " ").title(),
        "possible_illness": possible_illness_for_route(
            clinical_route.condition_id, clinical_route.symptom_ids
        ),
        "diagnosis_disclaimer": "This is not a diagnosis. A qualified clinician must confirm what illness you have.",
        "urgency": clinical_route.derived_urgency,
        "specialty": clinical_route.target_specialty,
        "required_department": department_for_specialty(
            clinical_route.target_specialty
        ),
        "severity": severity_for_urgency(clinical_route.derived_urgency),
        "severity_label": severity_for_urgency(clinical_route.derived_urgency).title(),
        "severity_message": severity_message_for_urgency(
            clinical_route.derived_urgency
        ),
        "messages": [
            f"I identified: {', '.join(clinical_route.symptom_ids) or 'no exact symptom match'}.",
            f"Routing source: {clinical_route.source}.",
        ],
        "nearest_clinic": {
            "tenant_id": str(route.tenant.id),
            "clinic_name": route.tenant.name,
            "address": route.tenant.state_location,
            "distance_km": round(route.distance_km, 2),
            "specialist_name": route.provider.full_name if route.provider else None,
            "match_basis": route.match_basis,
            "required_specialty": route.required_specialty,
            "emergency_capable": selected_candidate.has_emergency_capability,
        },
        "alternative_facilities": [
            {
                "tenant_id": str(item.tenant.id),
                "clinic_name": item.tenant.name,
                "address": item.tenant.state_location,
                "distance_km": round(item.distance_km or 0, 2),
                "match_basis": "; ".join(item.reasons[:2]),
            }
            for item in alternatives
        ],
        "appointment_slot": slot_payload,
        "ticket": {"id": str(ticket.id), "ticket_number": ticket.ticket_number},
    }
