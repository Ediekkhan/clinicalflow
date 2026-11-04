from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/public/pricing")
async def public_pricing() -> dict[str, Any]:
    return {
        "plans": [
            {
                "id": "pilot",
                "name": "Clinic Pilot",
                "price_label": "Let's talk",
                "description": "Queue, triage, patient tickets, and onboarding for one facility.",
                "cta_href": "/book-demo",
            },
            {
                "id": "network",
                "name": "Hospital Network",
                "price_label": "Custom",
                "description": "Multi-department workflows, scheduling, channels, and analytics.",
                "cta_href": "/book-demo",
            },
            {
                "id": "public",
                "name": "Public Health",
                "price_label": "Partnership",
                "description": "State-wide coordination and reporting for care networks.",
                "cta_href": "/book-demo",
            },
        ]
    }


@router.get("/public/blog-posts")
async def public_blog_posts() -> list[dict[str, str]]:
    return [
        {
            "id": "uyo-pilot",
            "category": "Clinic Operations",
            "title": "Reducing queue uncertainty in busy outpatient clinics",
            "excerpt": "How shared intake and live tickets improve the patient arrival experience.",
        },
        {
            "id": "shared-phone",
            "category": "Access",
            "title": "Designing healthcare workflows for shared family phones",
            "excerpt": "Protecting patient identity without blocking low-bandwidth access.",
        },
        {
            "id": "human-triage",
            "category": "Clinical Safety",
            "title": "Why automated triage still needs a human overtake control",
            "excerpt": "Supporting nurses when real-world urgency changes faster than software.",
        },
    ]


@router.get("/public/testimonials")
async def public_testimonials() -> list[dict[str, str]]:
    return []


@router.post(
    "/public/demo-requests", response_model=DemoRequestResponse, status_code=201
)
async def create_demo_request(
    payload: DemoRequestCreate, session: AsyncSession = Depends(get_db)
) -> DemoRequestResponse:
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    lead = DemoRequest(tenant_id=tenant_id, **payload.model_dump())
    session.add(lead)
    await session.commit()
    return DemoRequestResponse(
        id=lead.id, message="Thanks — your demo request has been received."
    )


@router.post("/public/enterprise-enquiries", status_code=201)
async def create_enterprise_enquiry(
    payload: EnterpriseEnquiryCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not payload.consent_to_contact:
        raise HTTPException(
            status_code=422, detail="Consent to be contacted is required"
        )
    tenant_id = uuid.UUID(public_tenant_id())
    await apply_tenant_context(session, tenant_id)
    idempotency_key = request.headers.get("x-idempotency-key")
    if idempotency_key:
        existing = await session.scalar(
            select(EnterpriseEnquiry).where(
                EnterpriseEnquiry.idempotency_key == idempotency_key
            )
        )
        if existing:
            return {"reference": existing.reference, "status": existing.status}
    reference = f"CF-ENT-{datetime.now(UTC):%Y%m%d}-{secrets.token_hex(3).upper()}"
    data = payload.model_dump(exclude={"consent_to_contact"})
    enquiry = EnterpriseEnquiry(
        tenant_id=tenant_id,
        reference=reference,
        idempotency_key=idempotency_key,
        data_json=json.dumps(data),
        consented_at=utc_now(),
    )
    session.add(enquiry)
    await session.flush()
    admins = (
        (
            await session.execute(
                select(AuthAccount).where(
                    AuthAccount.tenant_id == tenant_id,
                    AuthAccount.role == "admin",
                    AuthAccount.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    for admin in admins:
        notification = Notification(
            tenant_id=tenant_id,
            recipient_user_id=admin.id,
            recipient_account_id=admin.id,
            recipient_role="admin",
            event_type="ENTERPRISE_ENQUIRY_CREATED",
            title="New enterprise enquiry",
            body=f"New enquiry {reference} requires review.",
            payload_json=json.dumps({"reference": reference}),
        )
        session.add(notification)
        await session.flush()
        session.add(
            NotificationDelivery(
                notification_id=notification.id, channel="IN_APP", status="PENDING"
            )
        )
        session.add(
            OutboxEvent(
                tenant_id=tenant_id,
                aggregate_type="EnterpriseEnquiry",
                aggregate_id=enquiry.id,
                event_type="ENTERPRISE_ENQUIRY_CREATED",
                recipient_user_id=admin.id,
                payload_json=json.dumps(
                    {"reference": reference, "notification_id": str(notification.id)}
                ),
                classification="RESTRICTED",
            )
        )
    await write_audit_log(
        session,
        AuditAction.ENTERPRISE_ENQUIRY_CREATED,
        actor_id=None,
        actor_type="PUBLIC",
        tenant_id=str(tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="EnterpriseEnquiry",
        resource_id=str(enquiry.id),
        metadata={"reference": reference},
    )
    await session.commit()
    return {"reference": reference, "status": enquiry.status}
