from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403
from app.routes.sector_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/registry/facilities")
async def registry_facilities(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    service_code = str(request.query_params.get("service_code") or "").strip()
    specialty_code = str(request.query_params.get("specialty_code") or "").strip()
    facility_type = str(request.query_params.get("facility_type") or "").strip().upper()
    emergency = str(request.query_params.get("emergency_capable") or "").lower()
    query = (
        select(FacilityRegistry, Tenant)
        .join(Tenant, Tenant.id == FacilityRegistry.tenant_id)
        .where(
            FacilityRegistry.status == "ACTIVE",
            FacilityRegistry.accepts_patients.is_(True),
            Tenant.status == "ACTIVE",
            Tenant.accepts_patients.is_(True),
        )
    )
    if facility_type:
        query = query.where(FacilityRegistry.facility_type == facility_type)
    if emergency in {"true", "1"}:
        query = query.where(FacilityRegistry.emergency_capable.is_(True))
    if service_code or specialty_code:
        query = query.join(
            FacilityService, FacilityService.facility_registry_id == FacilityRegistry.id
        ).where(FacilityService.status == "ACTIVE")
        if service_code:
            query = query.where(FacilityService.service_code == service_code)
        if specialty_code:
            query = query.where(FacilityService.specialty_code == specialty_code)
    rows = (await session.execute(query.distinct().order_by(Tenant.name))).all()
    return {
        "items": [
            {
                "id": str(facility.id),
                "tenant_id": str(tenant.id),
                "name": tenant.name,
                "facility_type": facility.facility_type,
                "country": facility.country,
                "jurisdiction": facility.jurisdiction,
                "location": tenant.state_location,
                "latitude": tenant.latitude,
                "longitude": tenant.longitude,
                "emergency_capable": facility.emergency_capable,
                "capacity_status": facility.capacity_status,
            }
            for facility, tenant in rows
        ]
    }


@router.get("/registry/providers/{account_id}")
async def registry_provider(
    account_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_roles(
        request,
        session,
        {
            "doctor",
            "specialist",
            "nurse",
            "hospital_admin",
            "department_coordinator",
            "admin",
        },
    )
    provider = await session.scalar(
        select(ProviderRegistry).where(ProviderRegistry.account_id == account_id)
    )
    if not provider:
        target = await session.get(AuthAccount, account_id)
        if not target or target.role not in {
            "doctor",
            "specialist",
            "nurse",
            "lab",
            "pharmacy",
        }:
            raise HTTPException(
                status_code=404, detail="Provider registry record not found"
            )
        provider = await ensure_provider_registry(session, target)
        await session.commit()
    memberships = list(
        (
            await session.execute(
                select(StaffMembership).where(
                    StaffMembership.user_id == account_id,
                    StaffMembership.hospital_id == account.tenant_id,
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        "id": str(provider.id),
        "account_id": str(provider.account_id),
        "practitioner_identifier": provider.practitioner_identifier,
        "professional_role": provider.professional_role,
        "licence_jurisdiction": provider.licence_jurisdiction,
        "licence_number": provider.licence_number,
        "verification_status": provider.verification_status,
        "memberships": [
            {
                "id": str(item.id),
                "hospital_id": str(item.hospital_id),
                "department_id": item.department_id,
                "specialty_id": item.specialty_id,
                "status": item.verification_status,
            }
            for item in memberships
        ],
    }


@router.get("/country-packs/{country_code}/active")
async def active_country_pack(
    country_code: str, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    await require_account(request, session)
    code = country_code.upper()
    row = await session.scalar(
        select(CountryPack)
        .where(CountryPack.country_code == code, CountryPack.status == "ACTIVE")
        .order_by(CountryPack.effective_from.desc(), CountryPack.created_at.desc())
    )
    if not row and code == "NG":
        await country_policy(session, code)
        row = await session.scalar(
            select(CountryPack)
            .where(CountryPack.country_code == code, CountryPack.status == "ACTIVE")
            .order_by(CountryPack.created_at.desc())
        )
    if not row:
        raise HTTPException(status_code=404, detail="No active country pack")
    return {
        "country_code": row.country_code,
        "version": row.version,
        "policy": json.loads(row.policy_json),
        "requires_legal_review": row.requires_legal_review,
        "reviewed_by": row.reviewed_by,
    }


@router.get("/interoperability/mappings")
async def interoperability_mappings(
    request: Request, country_code: str = "NG", session: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    await require_account(request, session)
    rows = list(
        (
            await session.execute(
                select(InteroperabilityMapping)
                .join(
                    CountryPack,
                    CountryPack.id == InteroperabilityMapping.country_pack_id,
                )
                .where(
                    CountryPack.country_code == country_code.upper(),
                    CountryPack.status == "ACTIVE",
                    InteroperabilityMapping.status == "ACTIVE",
                )
                .order_by(InteroperabilityMapping.resource_type)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "resource_type": row.resource_type,
            "standard": row.standard,
            "version": row.version,
            "mapping": json.loads(row.mapping_json),
        }
        for row in rows
    ]


@router.post("/offline/mutations", status_code=202)
async def enqueue_offline_mutation(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    payload = await request.json()
    client_id, mutation_type = (
        str(payload.get("client_mutation_id") or "").strip(),
        str(payload.get("mutation_type") or "").upper(),
    )
    body = payload.get("payload")
    if (
        not client_id
        or mutation_type not in {"CLINICAL_TASK", "OBSERVATION"}
        or not isinstance(body, dict)
    ):
        raise HTTPException(
            status_code=422,
            detail="Client mutation ID, supported mutation type, and payload are required",
        )
    existing = await session.scalar(
        select(OfflineClinicalMutation).where(
            OfflineClinicalMutation.account_id == account.id,
            OfflineClinicalMutation.client_mutation_id == client_id,
        )
    )
    if existing:
        return {"id": str(existing.id), "status": existing.status, "duplicate": True}
    row = OfflineClinicalMutation(
        account_id=account.id,
        tenant_id=account.tenant_id,
        client_mutation_id=client_id,
        mutation_type=mutation_type,
        payload_json=json.dumps(body),
    )
    session.add(row)
    await session.commit()
    return {"id": str(row.id), "status": row.status, "duplicate": False}


@router.post("/offline/mutations/sync")
async def sync_offline_mutations(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    await require_staff_workspace(session, account)
    rows = list(
        (
            await session.execute(
                select(OfflineClinicalMutation)
                .where(
                    OfflineClinicalMutation.account_id == account.id,
                    OfflineClinicalMutation.status.in_(["PENDING", "FAILED"]),
                )
                .order_by(OfflineClinicalMutation.created_at)
                .limit(100)
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    synced, failed = 0, 0
    for row in rows:
        row.attempts += 1
        try:
            body = json.loads(row.payload_json)
            patient_id = parse_uuid(body.get("patient_id"), "patient_id")
            if row.mutation_type == "CLINICAL_TASK":
                description = str(body.get("description") or "").strip()
                if not description:
                    raise ValueError("Task description is required")
                session.add(
                    ClinicalTask(
                        patient_id=patient_id,
                        facility_id=account.tenant_id,
                        assignee_id=(
                            parse_uuid(body["assignee_id"], "assignee_id")
                            if body.get("assignee_id")
                            else None
                        ),
                        task_type=str(body.get("task_type") or "FOLLOW_UP"),
                        description=description,
                        due_at=(
                            parse_datetime(body["due_at"], "due_at")
                            if body.get("due_at")
                            else None
                        ),
                    )
                )
            else:
                if not all(
                    str(body.get(key) or "").strip()
                    for key in ("code", "display", "value")
                ):
                    raise ValueError(
                        "Observation code, display, and value are required"
                    )
                session.add(
                    ClinicalObservation(
                        patient_id=patient_id,
                        code=str(body["code"]),
                        display=str(body["display"]),
                        value=str(body["value"]),
                        unit=body.get("unit"),
                        abnormal_flag=body.get("abnormal_flag"),
                        observed_by_id=account.id,
                        observed_at=(
                            parse_datetime(body["observed_at"], "observed_at")
                            if body.get("observed_at")
                            else utc_now()
                        ),
                    )
                )
            row.status, row.synced_at, row.last_error = "SYNCED", utc_now(), None
            synced += 1
        except (ValueError, HTTPException, json.JSONDecodeError) as error:
            row.status, row.last_error = (
                "FAILED",
                str(getattr(error, "detail", error))[:1000],
            )
            failed += 1
    await session.commit()
    return {
        "synced": synced,
        "failed": failed,
        "remaining": max(0, len(rows) - synced - failed),
    }
