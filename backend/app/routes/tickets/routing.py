from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/tickets/{ticket_id}/routing")
async def hospital_ticket_routing(
    ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    _account, workspace, _tenant = await require_hospital_membership(request, session)
    ticket = await session.scalar(
        select(Ticket).where(
            Ticket.id == ticket_id, ticket_visible_to_tenant(workspace.hospital_id)
        )
    )
    decision = (
        await session.scalar(
            select(RoutingDecision).where(RoutingDecision.ticket_id == ticket_id)
        )
        if ticket
        else None
    )
    if not decision:
        raise HTTPException(
            status_code=404, detail="Routing decision not found in this workspace"
        )
    rows = (
        await session.execute(
            select(RoutingCandidate, Tenant)
            .join(Tenant, Tenant.id == RoutingCandidate.facility_id)
            .where(RoutingCandidate.routing_decision_id == decision.id)
            .order_by(RoutingCandidate.eligible.desc(), RoutingCandidate.rank.asc())
        )
    ).all()
    return {
        "ticket_id": str(ticket_id),
        "selected_facility_id": (
            str(decision.selected_facility_id)
            if decision.selected_facility_id
            else None
        ),
        "required_service": decision.required_service,
        "required_specialty": decision.required_specialty,
        "urgency": decision.urgency,
        "status": decision.status,
        "selection_reason": decision.selection_reason,
        "manual_override_reason": decision.manual_override_reason,
        "candidates": [
            {
                "facility_id": str(item.facility_id),
                "facility_name": tenant.name,
                "eligible": item.eligible,
                "rank": item.rank,
                "distance_km": item.distance_km,
                "score": item.suitability_score,
                "reasons": json.loads(item.reasons_json),
            }
            for item, tenant in rows
        ],
    }


@router.patch("/hospital/tickets/{ticket_id}/routing")
async def override_ticket_routing(
    ticket_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, workspace, _tenant = await require_hospital_membership(
        request, session, roles={"hospital_admin", "department_coordinator"}
    )
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 10:
        raise HTTPException(
            status_code=422, detail="A specific manual routing reason is required"
        )
    try:
        facility_id = uuid.UUID(str(payload.get("facility_id") or ""))
    except ValueError:
        raise HTTPException(
            status_code=422, detail="A valid destination facility is required"
        )
    ticket = await session.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id, ticket_visible_to_tenant(workspace.hospital_id))
        .with_for_update()
    )
    decision = (
        await session.scalar(
            select(RoutingDecision)
            .where(RoutingDecision.ticket_id == ticket_id)
            .with_for_update()
        )
        if ticket
        else None
    )
    if not ticket or not decision:
        raise HTTPException(
            status_code=404, detail="Routing decision not found in this workspace"
        )
    candidate = await session.scalar(
        select(RoutingCandidate).where(
            RoutingCandidate.routing_decision_id == decision.id,
            RoutingCandidate.facility_id == facility_id,
            RoutingCandidate.eligible.is_(True),
        )
    )
    if not candidate:
        raise HTTPException(
            status_code=422,
            detail="Manual override destination is not an eligible clinical candidate",
        )
    ticket.routed_tenant_id, ticket.route_distance_km = (
        facility_id,
        candidate.distance_km,
    )
    decision.selected_facility_id, decision.status, decision.manual_override_reason = (
        facility_id,
        "MANUALLY_OVERRIDDEN",
        reason,
    )
    decision.overridden_by_account_id, decision.overridden_at = account.id, utc_now()
    await write_audit_log(
        session,
        AuditAction.TICKET_ASSIGNED,
        actor_id=str(account.id),
        actor_type=account.role.upper(),
        tenant_id=str(workspace.hospital_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="RoutingDecision",
        resource_id=str(decision.id),
        metadata={
            "ticket_id": str(ticket.id),
            "destination_facility_id": str(facility_id),
            "reason": reason,
        },
    )
    await session.commit()
    return {
        "ticket_id": str(ticket.id),
        "selected_facility_id": str(facility_id),
        "status": decision.status,
        "reason": reason,
    }


@router.post("/hospital/tickets/{ticket_id}/facility-decision", status_code=201)
async def facility_ticket_decision(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, membership, _ = await require_hospital_membership(
        request, session, {"hospital_admin", "admin"}
    )
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    reason = str(payload.get("reason") or "").strip()
    if decision not in FACILITY_DECISION_STATES:
        raise HTTPException(
            status_code=422, detail="Decision must be ACCEPT, REJECT, or REDIRECT"
        )
    if decision in {"REJECT", "REDIRECT"} and len(reason) < 10:
        raise HTTPException(
            status_code=422,
            detail="A clear reason is required for rejection or redirection",
        )
    ticket = await session.scalar(
        select(Ticket)
        .where(
            Ticket.id == uuid.UUID(ticket_id),
            Ticket.routed_tenant_id == membership.hospital_id,
        )
        .with_for_update()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Routed ticket not found")
    if ticket.queue_status not in {"QUEUED", "ROUTED", "AWAITING_FACILITY_ACCEPTANCE"}:
        raise HTTPException(
            status_code=409, detail="Ticket can no longer receive a facility decision"
        )
    redirected_id = None
    if decision == "REDIRECT":
        try:
            redirected_id = uuid.UUID(str(payload.get("redirect_facility_id")))
        except (TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422, detail="A valid redirect facility is required"
            ) from error
        destination = await session.get(Tenant, redirected_id)
        destination_registry = await session.scalar(
            select(FacilityRegistry).where(FacilityRegistry.tenant_id == redirected_id)
        )
        if (
            not destination
            or destination.status != "ACTIVE"
            or destination.id == membership.hospital_id
            or not destination_registry
            or destination_registry.status != "ACTIVE"
            or not destination_registry.accepts_patients
        ):
            raise HTTPException(
                status_code=422,
                detail="Redirect facility must be a different active registered facility that accepts patients",
            )
    previous = ticket.queue_status
    next_status = FACILITY_DECISION_STATES[decision]
    ticket.queue_status = (
        "AWAITING_FACILITY_ACCEPTANCE" if decision == "REDIRECT" else next_status
    )
    if decision == "REDIRECT" and redirected_id:
        ticket.routed_tenant_id = redirected_id
    ticket.version += 1
    session.add(
        FacilityAcceptance(
            ticket_id=ticket.id,
            facility_id=membership.hospital_id,
            actor_account_id=account.id,
            actor_membership_id=membership.id,
            decision=decision,
            previous_status=previous,
            next_status=next_status,
            reason=reason or None,
            redirected_facility_id=redirected_id,
        )
    )
    session.add(
        OutboxEvent(
            tenant_id=membership.hospital_id,
            aggregate_type="Ticket",
            aggregate_id=ticket.id,
            event_type=f"facility.{decision.lower()}",
            payload_json=json.dumps(
                {
                    "ticket_id": str(ticket.id),
                    "decision": decision,
                    "redirected_facility_id": (
                        str(redirected_id) if redirected_id else None
                    ),
                }
            ),
            classification="RESTRICTED",
            status="PENDING",
        )
    )
    await session.commit()
    return {
        "ticket": build_ticket_response(ticket),
        "decision": decision,
        "reason": reason or None,
        "redirected_facility_id": redirected_id,
    }


@router.post("/hospital/tickets/{ticket_id}/transition")
async def transition_facility_ticket(
    ticket_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> TicketResponse:
    account, membership, _ = await require_hospital_membership(request, session)
    payload = await request.json()
    next_status = str(payload.get("status") or "").upper()
    ticket = await session.scalar(
        select(Ticket)
        .where(
            Ticket.id == uuid.UUID(ticket_id),
            Ticket.routed_tenant_id == membership.hospital_id,
        )
        .with_for_update()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Routed ticket not found")
    if next_status not in QUEUE_TRANSITIONS.get(ticket.queue_status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition from {ticket.queue_status} to {next_status}",
        )
    previous = ticket.queue_status
    ticket.queue_status = next_status
    ticket.version += 1
    session.add(
        FacilityAcceptance(
            ticket_id=ticket.id,
            facility_id=membership.hospital_id,
            actor_account_id=account.id,
            actor_membership_id=membership.id,
            decision="TRANSITION",
            previous_status=previous,
            next_status=next_status,
            reason=str(payload.get("reason") or "").strip() or None,
        )
    )
    event_type = (
        "patient.checked_in"
        if next_status == "CHECKED_IN"
        else "patient.status_changed"
    )
    session.add(
        OutboxEvent(
            tenant_id=membership.hospital_id,
            aggregate_type="Ticket",
            aggregate_id=ticket.id,
            event_type=event_type,
            payload_json=json.dumps(
                {
                    "ticket_id": str(ticket.id),
                    "previous_status": previous,
                    "status": next_status,
                }
            ),
            classification="RESTRICTED",
            status="PENDING",
        )
    )
    await session.commit()
    return build_ticket_response(ticket)
