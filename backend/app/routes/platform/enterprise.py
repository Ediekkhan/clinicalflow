from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/platform/enterprise-enquiries")
async def list_enterprise_enquiries(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    rows = (
        (
            await session.execute(
                select(EnterpriseEnquiry)
                .where(EnterpriseEnquiry.tenant_id == account.tenant_id)
                .order_by(EnterpriseEnquiry.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "reference": row.reference,
                "status": row.status,
                **json.loads(row.data_json),
                "created_at": row.created_at.isoformat(),
                "internal_notes": row.internal_notes,
                "assigned_to_id": (
                    str(row.assigned_to_id) if row.assigned_to_id else None
                ),
            }
            for row in rows
        ]
    }


@router.patch("/platform/enterprise-enquiries/{reference}")
async def update_enterprise_enquiry(
    reference: str,
    payload: EnterpriseEnquiryUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    row = await session.scalar(
        select(EnterpriseEnquiry)
        .where(
            EnterpriseEnquiry.reference == reference,
            EnterpriseEnquiry.tenant_id == account.tenant_id,
        )
        .with_for_update()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Enterprise enquiry not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(row, key, value)
    await write_audit_log(
        session,
        AuditAction.ENTERPRISE_ENQUIRY_UPDATED,
        actor_id=str(account.id),
        actor_type="STAFF",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "0.0.0.0",
        resource_type="EnterpriseEnquiry",
        resource_id=str(row.id),
        metadata={"reference": row.reference, "fields": list(changes)},
    )
    await session.commit()
    return {
        "reference": row.reference,
        "status": row.status,
        "internal_notes": row.internal_notes,
    }


@router.get("/platform/enterprise-enquiries/{reference}")
async def get_enterprise_enquiry(
    reference: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    row = await session.scalar(
        select(EnterpriseEnquiry).where(
            EnterpriseEnquiry.reference == reference,
            EnterpriseEnquiry.tenant_id == account.tenant_id,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="Enterprise enquiry not found")
    return {
        "reference": row.reference,
        "status": row.status,
        **json.loads(row.data_json),
        "internal_notes": row.internal_notes,
        "assigned_to_id": str(row.assigned_to_id) if row.assigned_to_id else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@router.get("/platform/enterprise-enquiries-report")
async def export_enterprise_enquiries(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    rows = (
        (
            await session.execute(
                select(EnterpriseEnquiry)
                .where(EnterpriseEnquiry.tenant_id == account.tenant_id)
                .order_by(EnterpriseEnquiry.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {
                "reference": row.reference,
                "status": row.status,
                "organization": json.loads(row.data_json).get(
                    "organization_legal_name"
                ),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
    }
