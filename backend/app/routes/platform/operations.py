from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post("/admin/maintenance/retention")
async def enforce_retention(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(request, session, {"admin"})
    now = utc_now()
    sessions = await session.execute(
        delete(AuthSession).where(
            AuthSession.refresh_expires_at
            < now - timedelta(days=settings.session_retention_days)
        )
    )
    audits = await session.execute(
        delete(AuditLog).where(
            AuditLog.tenant_id == account.tenant_id,
            AuditLog.timestamp < now - timedelta(days=settings.audit_retention_days),
        )
    )
    leads = await session.execute(
        delete(DemoRequest).where(
            DemoRequest.tenant_id == account.tenant_id,
            DemoRequest.created_at < now - timedelta(days=settings.lead_retention_days),
        )
    )
    await write_audit_log(
        session,
        AuditAction.DATA_DELETION_REQUEST,
        actor_id=str(account.id),
        actor_type="ADMIN",
        tenant_id=str(account.tenant_id),
        ip_address=request.client.host if request.client else "127.0.0.1",
        resource_type="RetentionJob",
        metadata={"policy": "configured_retention"},
    )
    await session.commit()
    return {
        "sessions_deleted": sessions.rowcount or 0,
        "audit_logs_deleted": audits.rowcount or 0,
        "demo_leads_deleted": leads.rowcount or 0,
    }


@router.post("/{entity}/{resource}", status_code=201)
async def create_operational_record(
    entity: str,
    resource: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if entity != "admin" or resource not in OPERATIONAL_RESOURCES:
        raise HTTPException(status_code=404, detail="Operational resource not found")
    account = await require_roles(request, session, {"admin"})
    payload = await request.json()
    title = str(payload.get("title") or "").strip()
    if len(title) < 2:
        raise HTTPException(status_code=422, detail="Record title is required")
    record = OperationalRecord(
        tenant_id=account.tenant_id,
        entity=entity,
        resource=resource,
        title=title,
        description=str(payload.get("description") or "").strip() or None,
        status=str(payload.get("status") or "ACTIVE").strip().upper(),
    )
    session.add(record)
    await session.commit()
    return {
        "id": str(record.id),
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "created_at": record.created_at,
    }


@router.patch("/{entity}/{resource}/{record_id}")
async def update_operational_record(
    entity: str,
    resource: str,
    record_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if entity != "admin" or resource not in OPERATIONAL_RESOURCES:
        raise HTTPException(status_code=404, detail="Operational resource not found")
    account = await require_roles(request, session, {"admin"})
    record = await session.scalar(
        select(OperationalRecord)
        .where(
            OperationalRecord.id == uuid.UUID(record_id),
            OperationalRecord.tenant_id == account.tenant_id,
            OperationalRecord.entity == entity,
            OperationalRecord.resource == resource,
        )
        .with_for_update()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Operational record not found")
    payload = await request.json()
    for field in ("title", "description", "status"):
        if field in payload:
            value = str(payload[field] or "").strip()
            if field == "title" and len(value) < 2:
                raise HTTPException(status_code=422, detail="Record title is required")
            setattr(
                record, field, value.upper() if field == "status" else value or None
            )
    record.updated_at = utc_now()
    await session.commit()
    return {
        "id": str(record.id),
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "updated_at": record.updated_at,
    }


@router.get("/{entity}/{resource}")
async def operational_portal(
    entity: str,
    resource: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    operational_entities = {"nurse", "clinic", "hospital"}
    sector_entities = {"pharmacy", "lab", "hmo", "moh", "admin"}
    if (
        entity not in operational_entities | sector_entities
        or resource not in OPERATIONAL_RESOURCES
    ):
        raise HTTPException(status_code=404, detail="Operational resource not found")
    role_map = {
        "pharmacy": {"pharmacy", "pharmacist", "admin"},
        "lab": {"laboratory", "lab_scientist", "lab_technician", "admin"},
        "hmo": {"hmo", "payer", "admin"},
        "moh": {"government", "moh", "admin"},
        "admin": {"admin"},
    }
    allowed_roles = role_map.get(entity, {"nurse", "doctor", "hospital_admin", "admin"})
    account = await require_roles(request, session, allowed_roles)
    tenant = await session.get(Tenant, account.tenant_id)
    tickets = list(
        (
            await session.execute(
                select(Ticket)
                .where(ticket_visible_to_tenant(account.tenant_id))
                .order_by(Ticket.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    providers = list(
        (
            await session.execute(
                select(Provider)
                .where(
                    Provider.tenant_id == account.tenant_id,
                    Provider.is_active.is_(True),
                )
                .order_by(Provider.full_name)
            )
        )
        .scalars()
        .all()
    )
    slots = list(
        (
            await session.execute(
                select(ProviderSlot, Provider)
                .join(Provider, Provider.id == ProviderSlot.provider_id)
                .where(ProviderSlot.tenant_id == account.tenant_id)
                .order_by(ProviderSlot.starts_at)
            )
        ).all()
    )
    appointments = list(
        (
            await session.execute(
                select(Appointment, ProviderSlot, Provider)
                .join(ProviderSlot, ProviderSlot.id == Appointment.slot_id)
                .join(Provider, Provider.id == ProviderSlot.provider_id)
                .where(Appointment.tenant_id == account.tenant_id)
                .order_by(ProviderSlot.starts_at)
            )
        ).all()
    )
    identity = {
        "name": tenant.name if tenant else entity.title(),
        "subtitle": tenant.state_location if tenant else "Operational workspace",
        "badge": account.role.replace("_", " ").title(),
        "initials": "".join(
            part[0] for part in (tenant.name if tenant else entity).split()[:2]
        ).upper(),
    }
    ticket_items = [
        {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "summary": ticket.raw_intake_text,
            "urgency_level": ticket.urgency_level,
            "queue_status": ticket.queue_status,
            "specialty": ticket.assigned_specialty,
            "created_at": ticket.created_at.isoformat(),
        }
        for ticket in tickets
    ]
    if entity in sector_entities:
        stored_records = list(
            (
                await session.execute(
                    select(OperationalRecord)
                    .where(
                        OperationalRecord.tenant_id == account.tenant_id,
                        OperationalRecord.entity == entity,
                        OperationalRecord.resource == resource,
                    )
                    .order_by(OperationalRecord.updated_at.desc())
                )
            )
            .scalars()
            .all()
        )
        accounts = list(
            (
                await session.execute(
                    select(AuthAccount)
                    .where(AuthAccount.tenant_id == account.tenant_id)
                    .order_by(AuthAccount.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        audit_rows = list(
            (
                await session.execute(
                    select(AuditLog)
                    .where(AuditLog.tenant_id == account.tenant_id)
                    .order_by(AuditLog.timestamp.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        unique_phones = sorted({ticket.customer_phone for ticket in tickets})
        appointment_items = [
            {
                "id": str(appointment.id),
                "title": f"{provider.full_name} · {appointment.customer_phone}",
                "status": appointment.status,
                "scheduled_at": slot.starts_at.isoformat(),
                "specialty": provider.specialty,
            }
            for appointment, slot, provider in appointments
        ]
        record_items = ticket_items
        if entity == "pharmacy":
            record_items = [
                {
                    **item,
                    "title": f"Medication review · {item['ticket_number']}",
                    "status": (
                        "DISPENSED" if item["queue_status"] == "RESOLVED" else "PENDING"
                    ),
                }
                for item in ticket_items
            ]
        elif entity == "lab":
            record_items = [
                {
                    **item,
                    "title": f"Diagnostic request · {item['ticket_number']}",
                    "status": (
                        "RELEASED" if item["queue_status"] == "RESOLVED" else "PENDING"
                    ),
                }
                for item in ticket_items
            ]
        elif entity == "hmo":
            record_items = appointment_items
        elif entity == "moh":
            condition_counts: dict[str, int] = {}
            for ticket in tickets:
                key = ticket.matched_condition_id or "unclassified"
                condition_counts[key] = condition_counts.get(key, 0) + 1
            record_items = [
                {
                    "id": key,
                    "title": key.replace("_", " ").title(),
                    "value": count,
                    "status": "ACTIVE",
                }
                for key, count in sorted(condition_counts.items())
            ]
        elif entity == "admin":
            if resource == "people":
                record_items = [
                    {
                        "id": str(row.id),
                        "full_name": f"{row.first_name} {row.last_name}",
                        "subtitle": row.role.replace("_", " ").title(),
                        "status": "ACTIVE" if row.is_active else "DISABLED",
                        "created_at": row.created_at.isoformat(),
                    }
                    for row in accounts
                ]
            elif resource == "messages":
                record_items = [
                    {
                        "id": str(row.id),
                        "title": row.action,
                        "body": f"{row.actor_type} · {row.resource_type or 'System'}",
                        "created_at": row.timestamp.isoformat(),
                        "status": "RECORDED",
                    }
                    for row in audit_rows
                ]
            elif resource == "vitals":
                return {
                    "identity": identity,
                    "items": [
                        {"id": "api", "title": "API", "status": "HEALTHY"},
                        {
                            "id": "redis",
                            "title": "Redis",
                            "status": (
                                "CONNECTED"
                                if request.app.state.redis.available
                                else "DEGRADED"
                            ),
                        },
                        {
                            "id": "neo4j",
                            "title": "Neo4j",
                            "status": (
                                "CONNECTED"
                                if request.app.state.knowledge_graph.available
                                else "FALLBACK"
                            ),
                        },
                    ],
                }
        stored_items = [
            {
                "id": str(row.id),
                "title": row.title,
                "description": row.description,
                "status": row.status,
                "updated_at": row.updated_at.isoformat(),
                "editable": True,
            }
            for row in stored_records
        ]
        record_items = stored_items + record_items
        if resource == "dashboard":
            return {
                "identity": identity,
                "stats": [
                    {
                        "title": "Patient records",
                        "value": len(unique_phones),
                        "tone": "sky",
                    },
                    {
                        "title": "Active tickets",
                        "value": sum(
                            ticket.queue_status != "RESOLVED" for ticket in tickets
                        ),
                        "tone": "amber",
                    },
                    {
                        "title": "Appointments",
                        "value": len(appointments),
                        "tone": "violet",
                    },
                    {"title": "Users", "value": len(accounts), "tone": "slate"},
                ],
                "activity": record_items[:8],
            }
        if resource == "settings":
            return {
                "identity": identity,
                "items": (
                    [
                        {
                            "id": str(tenant.id),
                            "title": tenant.name,
                            "subtitle": tenant.state_location,
                            "status": tenant.status,
                        }
                    ]
                    if tenant
                    else []
                ),
            }
        if resource == "facilities":
            return {
                "identity": identity,
                "items": (
                    [
                        {
                            "id": str(tenant.id),
                            "facility_name": tenant.name,
                            "location": tenant.state_location,
                            "status": tenant.status,
                        }
                    ]
                    if tenant
                    else []
                ),
            }
        if resource in {"members", "patients"}:
            return {
                "identity": identity,
                "items": [
                    {
                        "id": phone,
                        "name": f"Member {index + 1}",
                        "subtitle": phone,
                        "status": "ACTIVE",
                    }
                    for index, phone in enumerate(unique_phones)
                ],
            }
        if resource in {"claims", "payments"}:
            return {"identity": identity, "items": appointment_items}
        if resource in {"analytics", "utilization", "reports", "surveillance"}:
            return {"identity": identity, "chartData": record_items}
        if resource == "notifications":
            return {
                "identity": identity,
                "notifications": [
                    {**item, "type": "QUEUE_UPDATE", "is_read": False}
                    for item in record_items[:10]
                ],
            }
        return {"identity": identity, "items": record_items}
    if resource == "dashboard":
        active = [ticket for ticket in tickets if ticket.queue_status != "RESOLVED"]
        return {
            "identity": identity,
            "stats": [
                {"title": "Active patients", "value": len(active), "tone": "sky"},
                {
                    "title": "Critical",
                    "value": sum(
                        ticket.urgency_level == "CRITICAL"
                        and ticket.queue_status != "RESOLVED"
                        for ticket in tickets
                    ),
                    "tone": "rose",
                },
                {
                    "title": "Appointments",
                    "value": sum(
                        appointment.status == "BOOKED"
                        for appointment, _slot, _provider in appointments
                    ),
                    "tone": "amber",
                },
                {
                    "title": "Providers on roster",
                    "value": len(providers),
                    "tone": "slate",
                },
            ],
            "activity": ticket_items[:8],
        }
    if resource == "queue":
        return {
            "identity": identity,
            "items": [
                item for item in ticket_items if item["queue_status"] != "RESOLVED"
            ],
        }
    if resource in {"people", "doctors", "specialists"}:
        return {
            "identity": identity,
            "items": [
                {
                    "id": str(provider.id),
                    "full_name": provider.full_name,
                    "specialty": provider.specialty,
                    "status": "ACTIVE",
                    "subtitle": provider.room_label,
                }
                for provider in providers
            ],
        }
    if resource in {"patients", "vitals", "care-plans"}:
        return {"identity": identity, "items": ticket_items}
    if resource in {"appointments", "visits"}:
        return {
            "identity": identity,
            "items": [
                {
                    "id": str(appointment.id),
                    "title": f"{provider.full_name} · {provider.specialty}",
                    "status": appointment.status,
                    "scheduled_at": slot.starts_at.isoformat(),
                    "subtitle": f"{appointment.customer_phone} · {provider.room_label}",
                }
                for appointment, slot, provider in appointments
            ],
        }
    if resource == "schedule":
        return {
            "identity": identity,
            "items": [
                {
                    "id": str(slot.id),
                    "title": provider.full_name,
                    "specialty": provider.specialty,
                    "scheduled_at": slot.starts_at.isoformat(),
                    "status": (
                        "BOOKED"
                        if slot.is_booked
                        else "LOCKED" if slot.is_locked else "AVAILABLE"
                    ),
                    "subtitle": provider.room_label,
                }
                for slot, provider in slots
            ],
        }
    if resource == "notifications":
        return {
            "identity": identity,
            "notifications": [
                {
                    **item,
                    "title": f"Queue update · {item['ticket_number']}",
                    "type": "QUEUE_UPDATE",
                    "is_read": False,
                }
                for item in ticket_items[:10]
            ],
        }
    if resource == "settings":
        return {
            "identity": identity,
            "items": (
                [
                    {
                        "id": str(tenant.id),
                        "title": tenant.name,
                        "subtitle": tenant.state_location,
                        "status": tenant.status,
                    }
                ]
                if tenant
                else []
            ),
        }
    if resource == "departments":
        names = sorted(
            {ticket.assigned_specialty or "Front Desk" for ticket in tickets}
            | {provider.specialty for provider in providers}
        )
        return {
            "identity": identity,
            "items": [
                {
                    "id": name,
                    "name": name,
                    "status": "ACTIVE",
                    "summary": f"{sum((ticket.assigned_specialty or 'Front Desk') == name and ticket.queue_status != 'RESOLVED' for ticket in tickets)} active patients",
                }
                for name in names
            ],
        }
    condition_counts: dict[str, int] = {}
    for ticket in tickets:
        label = ticket.matched_condition_id or "unclassified"
        condition_counts[label] = condition_counts.get(label, 0) + 1
    return {
        "identity": identity,
        "chartData": [
            {
                "id": label,
                "title": label.replace("_", " ").title(),
                "value": count,
                "status": "ACTIVE",
            }
            for label, count in sorted(condition_counts.items())
        ],
    }
