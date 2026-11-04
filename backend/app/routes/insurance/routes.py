from __future__ import annotations

from fastapi import APIRouter

from app.routes.sector_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/coverage/eligibility", status_code=201)
async def check_eligibility(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    payload = await request.json()
    patient_id = (
        account.id
        if account.role == "patient"
        else parse_uuid(payload.get("patient_id"), "patient_id")
    )
    facility_id = (
        account.tenant_id
        if account.role != "patient"
        else parse_uuid(payload.get("facility_id"), "facility_id")
    )
    service_code, lawful_basis = (
        str(payload.get("service_code") or "").strip(),
        str(payload.get("lawful_basis") or "").strip(),
    )
    if not service_code or not lawful_basis:
        raise HTTPException(
            status_code=422, detail="Service code and lawful basis are required"
        )
    now, emergency = utc_now(), bool(payload.get("emergency"))
    coverages = list(
        (
            await session.execute(
                select(MemberCoverage)
                .where(
                    MemberCoverage.patient_id == patient_id,
                    MemberCoverage.status == "ACTIVE",
                    MemberCoverage.starts_at <= now,
                    or_(
                        MemberCoverage.ends_at.is_(None), MemberCoverage.ends_at >= now
                    ),
                )
                .order_by(MemberCoverage.starts_at.desc())
            )
        )
        .scalars()
        .all()
    )
    requested_coverage = (
        parse_uuid(payload["coverage_id"], "coverage_id")
        if payload.get("coverage_id")
        else None
    )
    coverage = next(
        (
            item
            for item in coverages
            if not requested_coverage or item.id == requested_coverage
        ),
        None,
    )
    payer_id = coverage.payer_id if coverage else None
    row = EligibilityRequest(
        patient_id=patient_id,
        facility_id=facility_id,
        payer_id=payer_id,
        coverage_id=coverage.id if coverage else None,
        service_code=service_code,
        emergency=emergency,
        lawful_basis=lawful_basis,
        requested_by_id=account.id,
    )
    session.add(row)
    await session.flush()
    eligible, reason, currency = (
        False,
        "No active coverage found; self-pay remains available.",
        "NGN",
    )
    if coverage:
        plan = await session.get(HealthPlan, coverage.plan_id)
        contract = await session.scalar(
            select(ProviderContract).where(
                ProviderContract.payer_id == coverage.payer_id,
                ProviderContract.facility_id == facility_id,
                ProviderContract.status == "ACTIVE",
                ProviderContract.starts_at <= now,
                or_(
                    ProviderContract.ends_at.is_(None), ProviderContract.ends_at >= now
                ),
            )
        )
        benefit = await session.scalar(
            select(Benefit).where(
                Benefit.plan_id == coverage.plan_id,
                Benefit.service_code == service_code,
            )
        )
        eligible = bool(plan and plan.status == "ACTIVE" and contract and benefit)
        reason, currency = (
            "Coverage and provider contract are active."
            if eligible
            else "The service or provider contract is not covered."
        ), (plan.currency if plan else "NGN")
    if emergency and not eligible:
        reason += " Emergency care must not be delayed for authorization."
    response = EligibilityResponse(
        request_id=row.id, eligible=eligible, reason=reason, currency=currency
    )
    session.add(response)
    await session.commit()
    return {
        "request_id": str(row.id),
        "eligible": eligible,
        "reason": reason,
        "coverage_id": str(coverage.id) if coverage else None,
        "self_pay_available": not eligible,
        "care_must_continue": emergency,
    }


@router.get("/patients/me/coverage")
async def my_coverage(
    request: Request, session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    account = await require_roles(request, session, {"patient"})
    rows = list(
        (
            await session.execute(
                select(MemberCoverage, HealthPlan, PayerOrganization)
                .join(HealthPlan, HealthPlan.id == MemberCoverage.plan_id)
                .join(
                    PayerOrganization, PayerOrganization.id == MemberCoverage.payer_id
                )
                .where(MemberCoverage.patient_id == account.id)
                .order_by(MemberCoverage.starts_at.desc())
            )
        ).all()
    )
    return [
        {
            "id": str(row.id),
            "payer": payer.legal_name,
            "plan": plan.name,
            "member_number": row.member_number,
            "status": row.status,
            "starts_at": row.starts_at,
            "ends_at": row.ends_at,
        }
        for row, plan, payer in rows
    ]


@router.post("/authorizations", status_code=201)
async def create_authorization(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    payload = await request.json()
    coverage = await session.get(
        MemberCoverage, parse_uuid(payload.get("coverage_id"), "coverage_id")
    )
    service_code = str(payload.get("service_code") or "").strip()
    if not coverage or not service_code:
        raise HTTPException(
            status_code=422, detail="Active coverage and service code are required"
        )
    if account.role == "patient" and coverage.patient_id != account.id:
        raise HTTPException(status_code=403, detail="Coverage access denied")
    row = PriorAuthorization(
        coverage_id=coverage.id,
        facility_id=account.tenant_id,
        service_code=service_code,
        minimum_clinical_summary=str(
            payload.get("minimum_clinical_summary") or ""
        ).strip()
        or None,
        emergency=bool(payload.get("emergency")),
    )
    session.add(row)
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "emergency_care_must_continue": row.emergency,
    }


@router.patch("/hmo/authorizations/{authorization_id}/decision")
async def decide_authorization(
    authorization_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, payer = await require_payer(request, session)
    row = await session.scalar(
        select(PriorAuthorization)
        .join(MemberCoverage, MemberCoverage.id == PriorAuthorization.coverage_id)
        .where(
            PriorAuthorization.id == parse_uuid(authorization_id, "authorization_id"),
            MemberCoverage.payer_id == payer.id,
        )
        .with_for_update()
    )
    payload = await request.json()
    decision, reason = (
        str(payload.get("decision") or "").upper(),
        str(payload.get("reason") or "").strip(),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Authorization not found")
    if decision not in {"APPROVED", "DENIED"} or len(reason) < 3:
        raise HTTPException(
            status_code=422,
            detail="APPROVED or DENIED decision and a reason are required",
        )
    row.status, row.reason, row.decided_by_id, row.decided_at = (
        decision,
        reason,
        account.id,
        utc_now(),
    )
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "reason": row.reason,
        "emergency_care_must_continue": row.emergency,
    }


@router.post("/claims", status_code=201)
async def submit_claim(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role == "patient":
        raise HTTPException(
            status_code=403, detail="Claims must be submitted by an authorized facility"
        )
    payload = await request.json()
    coverage = await session.get(
        MemberCoverage, parse_uuid(payload.get("coverage_id"), "coverage_id")
    )
    items = payload.get("items")
    reference, lawful_basis = (
        str(payload.get("external_reference") or "").strip(),
        str(payload.get("lawful_basis") or "").strip(),
    )
    if (
        not coverage
        or not reference
        or not lawful_basis
        or not isinstance(items, list)
        or not items
    ):
        raise HTTPException(
            status_code=422,
            detail="Coverage, unique reference, lawful basis, and claim items are required",
        )
    if await session.scalar(
        select(InsuranceClaim.id).where(
            InsuranceClaim.payer_id == coverage.payer_id,
            InsuranceClaim.external_reference == reference,
        )
    ):
        raise HTTPException(status_code=409, detail="Duplicate claim reference")
    values = []
    for value in items:
        amount, quantity = int(value.get("amount_minor") or 0), int(
            value.get("quantity") or 1
        )
        if (
            not str(value.get("service_code") or "").strip()
            or amount <= 0
            or quantity <= 0
        ):
            raise HTTPException(
                status_code=422,
                detail="Every claim item requires a service code, positive amount, and quantity",
            )
        values.append((str(value["service_code"]).strip(), amount, quantity))
    row = InsuranceClaim(
        payer_id=coverage.payer_id,
        coverage_id=coverage.id,
        facility_id=account.tenant_id,
        patient_id=coverage.patient_id,
        external_reference=reference,
        total_minor=sum(amount * quantity for _, amount, quantity in values),
        currency=str(payload.get("currency") or "NGN").upper(),
        lawful_basis=lawful_basis,
    )
    session.add(row)
    await session.flush()
    session.add_all(
        [
            ClaimItem(
                claim_id=row.id,
                service_code=code,
                amount_minor=amount,
                quantity=quantity,
            )
            for code, amount, quantity in values
        ]
    )
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "total_minor": row.total_minor,
        "currency": row.currency,
    }


@router.patch("/hmo/claims/{claim_id}/decision")
async def decide_claim(
    claim_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account, payer = await require_payer(request, session)
    row = await session.scalar(
        select(InsuranceClaim)
        .where(
            InsuranceClaim.id == parse_uuid(claim_id, "claim_id"),
            InsuranceClaim.payer_id == payer.id,
        )
        .with_for_update()
    )
    payload = await request.json()
    decision, reason = (
        str(payload.get("decision") or "").upper(),
        str(payload.get("reason") or "").strip(),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Claim not found")
    if decision not in {"APPROVED", "PARTIALLY_APPROVED", "DENIED"} or len(reason) < 3:
        raise HTTPException(
            status_code=422, detail="A supported decision and reason are required"
        )
    approved = int(payload.get("approved_minor") or 0)
    if (
        approved < 0
        or approved > row.total_minor
        or (decision == "APPROVED" and approved != row.total_minor)
    ):
        raise HTTPException(
            status_code=422, detail="Approved amount is inconsistent with the decision"
        )
    if await session.scalar(
        select(ClaimResponse.id).where(ClaimResponse.claim_id == row.id)
    ):
        raise HTTPException(status_code=409, detail="Claim has already been decided")
    response = ClaimResponse(
        claim_id=row.id,
        decision=decision,
        approved_minor=approved,
        reason=reason,
        decided_by_id=account.id,
    )
    session.add(response)
    row.status = decision
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "approved_minor": approved,
        "reason": reason,
    }


@router.post("/claims/{claim_id}/appeals", status_code=201)
async def appeal_claim(
    claim_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    row = await session.get(InsuranceClaim, parse_uuid(claim_id, "claim_id"))
    payload = await request.json()
    reason = str(payload.get("reason") or "").strip()
    if (
        not row
        or row.facility_id != account.tenant_id
        or row.status not in {"DENIED", "PARTIALLY_APPROVED"}
        or len(reason) < 5
    ):
        raise HTTPException(
            status_code=422,
            detail="A denied facility claim and appeal reason are required",
        )
    appeal = ClaimAppeal(claim_id=row.id, submitted_by_id=account.id, reason=reason)
    session.add(appeal)
    await session.commit()
    return {"id": str(appeal.id), "status": appeal.status}


@router.get("/hmo/{resource}")
async def hmo_resource(
    resource: str, request: Request, session: AsyncSession = Depends(get_db)
) -> Any:
    account, payer = await require_payer(request, session)
    if resource == "dashboard":
        claims = await session.scalar(
            select(func.count())
            .select_from(InsuranceClaim)
            .where(InsuranceClaim.payer_id == payer.id)
        )
        members = await session.scalar(
            select(func.count())
            .select_from(MemberCoverage)
            .where(
                MemberCoverage.payer_id == payer.id, MemberCoverage.status == "ACTIVE"
            )
        )
        pending = await session.scalar(
            select(func.count())
            .select_from(PriorAuthorization)
            .join(MemberCoverage, MemberCoverage.id == PriorAuthorization.coverage_id)
            .where(
                MemberCoverage.payer_id == payer.id,
                PriorAuthorization.status == "REQUESTED",
            )
        )
        return {
            "stats": {
                "claims": claims,
                "members": members,
                "pending_authorizations": pending,
            }
        }
    if resource in {"members", "enrollees"}:
        rows = list(
            (
                await session.execute(
                    select(MemberCoverage)
                    .where(MemberCoverage.payer_id == payer.id)
                    .order_by(MemberCoverage.starts_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(row.id),
                "patient_id": str(row.patient_id),
                "member_number": row.member_number,
                "status": row.status,
                "starts_at": row.starts_at,
                "ends_at": row.ends_at,
            }
            for row in rows
        ]
    if resource == "claims":
        rows = list(
            (
                await session.execute(
                    select(InsuranceClaim)
                    .where(InsuranceClaim.payer_id == payer.id)
                    .order_by(InsuranceClaim.submitted_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(row.id),
                "external_reference": row.external_reference,
                "status": row.status,
                "total_minor": row.total_minor,
                "currency": row.currency,
                "submitted_at": row.submitted_at,
            }
            for row in rows
        ]
    if resource == "authorizations":
        rows = list(
            (
                await session.execute(
                    select(PriorAuthorization)
                    .join(
                        MemberCoverage,
                        MemberCoverage.id == PriorAuthorization.coverage_id,
                    )
                    .where(MemberCoverage.payer_id == payer.id)
                    .order_by(PriorAuthorization.created_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(row.id),
                "service_code": row.service_code,
                "status": row.status,
                "emergency": row.emergency,
                "reason": row.reason,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    if resource in {
        "analytics",
        "utilization",
        "payments",
        "facilities",
        "notifications",
        "settings",
    }:
        return []
    raise HTTPException(status_code=404, detail="Payer resource not found")
