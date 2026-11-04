from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/billing/status")
async def billing_status(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    return {
        "enabled": settings.enable_billing_module,
        "organization_id": str(account.tenant_id),
        "plan": "FREE",
        "subscription_status": "INACTIVE",
    }


@router.get("/onboarding/pro/draft")
async def get_pro_onboarding_draft(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    draft = await session.scalar(
        select(OrganizationOnboardingDraft).where(
            OrganizationOnboardingDraft.account_id == account.id
        )
    )
    return {
        "draft": (
            {
                "id": str(draft.id),
                "organization_type": draft.organization_type,
                "current_step": draft.current_step,
                "country": draft.country,
                "data": json.loads(draft.draft_data_json),
            }
            if draft
            else None
        )
    }


@router.put("/onboarding/pro/draft")
async def save_pro_onboarding_draft(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    payload = await request.json()
    draft = await session.scalar(
        select(OrganizationOnboardingDraft)
        .where(OrganizationOnboardingDraft.account_id == account.id)
        .with_for_update()
    )
    if not draft:
        draft = OrganizationOnboardingDraft(account_id=account.id, draft_data_json="{}")
        session.add(draft)
    draft.organization_type = (
        str(payload.get("organization_type") or draft.organization_type or "")[:64]
        or None
    )
    draft.current_step = max(
        1, min(6, int(payload.get("current_step") or draft.current_step))
    )
    draft.country = (
        str(payload.get("country") or draft.country or "")[:2].upper() or None
    )
    draft.draft_data_json = json.dumps(payload.get("data") or {}, ensure_ascii=True)
    await session.commit()
    return {"id": str(draft.id), "current_step": draft.current_step, "saved": True}


@router.get("/onboarding/pro/status")
async def pro_onboarding_status(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    application = await session.scalar(
        select(SignupApplication)
        .where(SignupApplication.account_id == account.id)
        .order_by(SignupApplication.updated_at.desc())
    )
    return {
        "account_verification": (
            "VERIFIED"
            if account.email_verified_at or account.phone_verified_at
            else "PENDING"
        ),
        "organization_application": application.status if application else "DRAFT",
        "licence_verification": "PENDING",
        "document_review": "PENDING",
        "payment": "NOT_STARTED",
        "workspace_activation": "RESTRICTED",
    }


@router.post("/billing/checkout")
async def create_billing_checkout(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    if not settings.enable_billing_module:
        raise HTTPException(
            status_code=503,
            detail="Billing is not configured. Add a production payment provider before enabling checkout.",
        )
    raise HTTPException(
        status_code=501, detail="No verified payment provider adapter is configured"
    )


@router.post("/billing/webhooks/{provider}")
async def payment_webhook(
    provider: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    provider_code = provider.upper()
    if provider_code not in {"STRIPE", "PAYSTACK"}:
        raise HTTPException(status_code=404, detail="Unsupported payment provider")
    body = await request.body()
    signature = (
        request.headers.get("stripe-signature")
        if provider_code == "STRIPE"
        else request.headers.get("x-paystack-signature")
    )
    adapter = provider_for_country("US" if provider_code == "STRIPE" else "NG")
    if adapter.name != provider_code or not adapter.verify_webhook(body, signature):
        raise HTTPException(status_code=401, detail="Invalid payment webhook signature")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON") from error
    event_id = str(payload.get("id") or payload.get("data", {}).get("reference") or "")
    if not event_id:
        raise HTTPException(status_code=400, detail="Webhook event ID is required")
    existing = await session.scalar(
        select(PaymentWebhookEvent).where(
            PaymentWebhookEvent.provider == provider_code,
            PaymentWebhookEvent.provider_event_id == event_id,
        )
    )
    if existing:
        return {"status": "already_processed"}
    event = PaymentWebhookEvent(
        provider=provider_code,
        provider_event_id=event_id,
        event_type=str(payload.get("type") or payload.get("event") or "unknown"),
        payload_hash=hashlib.sha256(body).hexdigest(),
        processing_status="PROCESSED",
        processed_at=utc_now(),
    )
    session.add(event)
    event_name = str(payload.get("type") or payload.get("event") or "").lower()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    data_object = data.get("object") if isinstance(data.get("object"), dict) else data
    provider_reference = str(
        data_object.get("id")
        or data_object.get("reference")
        or data_object.get("session_id")
        or ""
    )
    checkout = (
        await session.scalar(
            select(CheckoutSession)
            .where(
                CheckoutSession.provider == provider_code,
                CheckoutSession.provider_reference == provider_reference,
            )
            .with_for_update()
        )
        if provider_reference
        else None
    )
    if checkout:
        if any(
            token in event_name
            for token in ("completed", "success", "paid", "charge.success")
        ):
            checkout.status = "COMPLETED"
            checkout.completed_at = utc_now()
        elif any(token in event_name for token in ("failed", "failure", "declined")):
            checkout.status = "FAILED"
        if event_name in {
            "checkout.session.completed",
            "charge.success",
            "payment.success",
        }:
            session.add(
                PaymentAttempt(
                    checkout_session_id=checkout.id,
                    provider_transaction_reference=provider_reference,
                    amount_minor=checkout.amount_minor,
                    currency=checkout.currency,
                    status="SUCCEEDED",
                )
            )
            session.add(
                OutboxEvent(
                    tenant_id=checkout.organization_id,
                    aggregate_type="CheckoutSession",
                    aggregate_id=checkout.id,
                    event_type="PAYMENT_SUCCEEDED",
                    payload_json=json.dumps(
                        {"checkout_reference": checkout.public_reference}
                    ),
                    classification="RESTRICTED",
                )
            )
    await session.commit()
    return {"status": "accepted"}


@router.post("/billing/payments/{payment_id}/refunds")
async def request_refund(
    payment_id: str,
    payload: RefundCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    try:
        payment_uuid = uuid.UUID(payment_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid payment ID") from error
    payment = await session.scalar(
        select(PaymentAttempt)
        .join(CheckoutSession, CheckoutSession.id == PaymentAttempt.checkout_session_id)
        .where(
            PaymentAttempt.id == payment_uuid,
            CheckoutSession.organization_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not payment or payment.status != "SUCCEEDED":
        raise HTTPException(status_code=404, detail="Refundable payment not found")
    idempotency_key = request.headers.get("x-idempotency-key")
    if idempotency_key:
        existing = await session.scalar(
            select(RefundRecord).where(RefundRecord.idempotency_key == idempotency_key)
        )
        if existing:
            return {"refund_id": str(existing.id), "status": existing.status}
    refunds = list(
        (
            await session.scalars(
                select(RefundRecord).where(
                    RefundRecord.payment_attempt_id == payment.id,
                    RefundRecord.status.not_in({"FAILED", "CANCELLED"}),
                )
            )
        ).all()
    )
    refundable = payment.amount_minor - sum(item.amount_minor for item in refunds)
    amount = payload.amount_minor or refundable
    if amount > refundable:
        raise HTTPException(status_code=422, detail="Refund exceeds refundable balance")
    refund = RefundRecord(
        payment_attempt_id=payment.id,
        amount_minor=amount,
        currency=payment.currency,
        reason=payload.reason,
        requested_by_id=account.id,
        idempotency_key=idempotency_key,
    )
    session.add(refund)
    await session.commit()
    return {
        "refund_id": str(refund.id),
        "status": refund.status,
        "amount_minor": refund.amount_minor,
    }


@router.post("/billing/refunds/{refund_id}/approve")
async def approve_refund(
    refund_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    try:
        refund_uuid = uuid.UUID(refund_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid refund ID") from error
    refund = await session.scalar(
        select(RefundRecord)
        .join(PaymentAttempt)
        .join(CheckoutSession, CheckoutSession.id == PaymentAttempt.checkout_session_id)
        .where(
            RefundRecord.id == refund_uuid,
            CheckoutSession.organization_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not refund or refund.status != "REQUESTED":
        raise HTTPException(status_code=409, detail="Refund is not awaiting approval")
    refund.authorized_by_id = account.id
    refund.status = "APPROVED"
    await session.commit()
    return {"refund_id": str(refund.id), "status": refund.status}


@router.post("/billing/refunds/{refund_id}/submit")
async def submit_refund(
    refund_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    try:
        refund_uuid = uuid.UUID(refund_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid refund ID") from error
    refund = await session.scalar(
        select(RefundRecord)
        .join(PaymentAttempt)
        .join(CheckoutSession, CheckoutSession.id == PaymentAttempt.checkout_session_id)
        .where(
            RefundRecord.id == refund_uuid,
            CheckoutSession.organization_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not refund or refund.status != "APPROVED":
        raise HTTPException(
            status_code=409, detail="Refund must be approved before submission"
        )
    payment = await session.scalar(
        select(PaymentAttempt).where(PaymentAttempt.id == refund.payment_attempt_id)
    )
    checkout = (
        await session.scalar(
            select(CheckoutSession).where(
                CheckoutSession.id == payment.checkout_session_id
            )
        )
        if payment
        else None
    )
    if not payment or not checkout or not payment.provider_transaction_reference:
        raise HTTPException(
            status_code=409, detail="Payment provider reference is unavailable"
        )
    try:
        provider = provider_for_name(checkout.provider)
        result = await provider.create_refund(
            transaction_reference=payment.provider_transaction_reference,
            amount_minor=refund.amount_minor,
            currency=refund.currency,
            reference=str(refund.id),
        )
    except PaymentProviderError as error:
        refund.status = "FAILED"
        await session.commit()
        raise HTTPException(status_code=502, detail=str(error)) from error
    refund.provider_refund_reference = result.get("provider_reference")
    refund.status = (
        result.get("status")
        if result.get("status") in {"PENDING", "SUCCEEDED", "FAILED"}
        else "PENDING"
    )
    await session.commit()
    return {
        "refund_id": str(refund.id),
        "status": refund.status,
        "provider_refund_reference": refund.provider_refund_reference,
    }


@router.get("/billing/refunds")
async def list_refunds(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    rows = (
        (
            await session.execute(
                select(RefundRecord)
                .join(PaymentAttempt)
                .join(
                    CheckoutSession,
                    CheckoutSession.id == PaymentAttempt.checkout_session_id,
                )
                .where(CheckoutSession.organization_id == account.tenant_id)
                .order_by(RefundRecord.requested_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "id": str(row.id),
                "amount_minor": row.amount_minor,
                "currency": row.currency,
                "status": row.status,
                "reason": row.reason,
                "requested_at": row.requested_at.isoformat(),
            }
            for row in rows
        ]
    }


@router.get("/billing/refunds/{refund_id}")
async def get_refund(
    refund_id: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    try:
        refund_uuid = uuid.UUID(refund_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid refund ID") from error
    row = await session.scalar(
        select(RefundRecord)
        .join(PaymentAttempt)
        .join(CheckoutSession, CheckoutSession.id == PaymentAttempt.checkout_session_id)
        .where(
            RefundRecord.id == refund_uuid,
            CheckoutSession.organization_id == account.tenant_id,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Refund not found")
    return {
        "id": str(row.id),
        "status": row.status,
        "amount_minor": row.amount_minor,
        "currency": row.currency,
        "reason": row.reason,
        "requested_by_id": str(row.requested_by_id) if row.requested_by_id else None,
        "authorized_by_id": str(row.authorized_by_id) if row.authorized_by_id else None,
    }


@router.post("/billing/reconciliation/run")
async def run_reconciliation(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    pending = await session.scalar(
        select(func.count(PaymentAttempt.id))
        .join(CheckoutSession, CheckoutSession.id == PaymentAttempt.checkout_session_id)
        .where(
            CheckoutSession.organization_id == account.tenant_id,
            PaymentAttempt.status == "PENDING",
        )
    )
    return {"status": "queued", "pending_attempts": int(pending or 0)}


@router.get("/billing/reconciliation/issues")
async def list_reconciliation_issues(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    rows = (
        await session.scalars(
            select(ReconciliationIssue)
            .where(ReconciliationIssue.tenant_id == account.tenant_id)
            .order_by(ReconciliationIssue.created_at.desc())
        )
    ).all()
    return {
        "items": [
            {
                "id": str(row.id),
                "provider": row.provider,
                "provider_reference": row.provider_reference,
                "status": row.status,
                "local_status": row.local_status,
                "provider_status": row.provider_status,
            }
            for row in rows
        ]
    }


@router.post("/billing/reconciliation/issues/{issue_id}/resolve")
async def resolve_reconciliation_issue(
    issue_id: str,
    payload: ReconciliationResolve,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    try:
        issue_uuid = uuid.UUID(issue_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400, detail="Invalid reconciliation issue ID"
        ) from error
    row = await session.scalar(
        select(ReconciliationIssue)
        .where(
            ReconciliationIssue.id == issue_uuid,
            ReconciliationIssue.tenant_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not row or row.status != "OPEN":
        raise HTTPException(status_code=409, detail="Reconciliation issue is not open")
    row.status = "RESOLVED"
    row.resolution = payload.resolution
    row.resolved_by_id = account.id
    row.resolved_at = utc_now()
    await session.commit()
    return {"id": str(row.id), "status": row.status}
