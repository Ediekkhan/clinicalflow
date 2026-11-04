from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/hospital/settings")
async def hospital_settings(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(
        request, session, {"doctor", "nurse", "hospital_admin", "admin"}
    )
    tenant = await session.get(Tenant, account.tenant_id)
    staff = list(
        (
            await session.execute(
                select(AuthAccount).where(
                    AuthAccount.tenant_id == account.tenant_id,
                    AuthAccount.role.in_(
                        ["doctor", "nurse", "hospital_admin", "admin"]
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        "facility_name": tenant.name if tenant else "Hospital",
        "intake_paused": not await tenant_control(
            session, account.tenant_id, "intake_enabled", True
        ),
        "sms_route": "SIGNED_WEBHOOK",
        "whatsapp_enabled": await tenant_control(
            session, account.tenant_id, "whatsapp_enabled", True
        ),
        "staff": [
            {
                "id": str(row.id),
                "name": f"{row.first_name} {row.last_name}",
                "role": row.role,
                "scope": "Tenant",
            }
            for row in staff
        ],
    }


@router.patch("/hospital/settings")
async def update_hospital_settings(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"hospital_admin", "admin"})
    payload = await request.json()
    changes = (
        {"intake_enabled": not bool(payload["intake_paused"])}
        if "intake_paused" in payload
        else {}
    )
    if "whatsapp_enabled" in payload:
        changes["whatsapp_enabled"] = bool(payload["whatsapp_enabled"])
    for name, enabled in changes.items():
        record = await session.scalar(
            select(OperationalRecord)
            .where(
                OperationalRecord.tenant_id == account.tenant_id,
                OperationalRecord.entity == "system",
                OperationalRecord.resource == "settings",
                OperationalRecord.title == name,
            )
            .with_for_update()
        )
        if record:
            record.status = "ENABLED" if enabled else "DISABLED"
            record.updated_at = utc_now()
        else:
            session.add(
                OperationalRecord(
                    tenant_id=account.tenant_id,
                    entity="system",
                    resource="settings",
                    title=name,
                    description="Tenant runtime control",
                    status="ENABLED" if enabled else "DISABLED",
                )
            )
    await write_audit_log(
        session,
        (
            AuditAction.KILL_SWITCH_TOGGLED
            if "intake_enabled" in changes
            else AuditAction.TENANT_SETTINGS_CHANGED
        ),
        actor_id=str(account.id),
        actor_type=account.role.upper(),
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="TenantSettings",
        metadata={"controls": list(changes)},
    )
    await session.commit()
    return await hospital_settings(request, session)
