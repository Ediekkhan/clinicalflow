from __future__ import annotations

from fastapi import APIRouter

from app.routes.sector_helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.get("/moh/{resource}")
async def government_resource(
    resource: str,
    request: Request,
    jurisdiction: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> Any:
    account = await require_account(request, session)
    scope = await government_scope(session, account, jurisdiction)
    prefix = jurisdiction or scope.jurisdiction_code
    if resource == "dashboard":
        reports = await session.scalar(
            select(func.count())
            .select_from(MandatoryDiseaseReport)
            .where(MandatoryDiseaseReport.jurisdiction_code.like(f"{prefix}%"))
        )
        alerts = 0
        return {
            "stats": {"submitted_reports": reports, "active_alerts": alerts},
            "jurisdiction": prefix,
            "data_mode": "AGGREGATE",
        }
    if resource in {"reports", "surveillance"}:
        threshold = int(
            nested_policy(
                await country_policy(session),
                "mandatory_reporting",
                "small_cell_suppression",
                default=5,
            )
        )
        rows = list(
            (
                await session.execute(
                    select(MandatoryDiseaseReport)
                    .where(MandatoryDiseaseReport.jurisdiction_code.like(f"{prefix}%"))
                    .order_by(MandatoryDiseaseReport.submitted_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(row.id),
                "jurisdiction_code": row.jurisdiction_code,
                "report_type": row.report_type,
                "condition_code": row.condition_code,
                "reporting_period": row.reporting_period,
                "aggregate_count": (
                    None if row.aggregate_count < threshold else row.aggregate_count
                ),
                "suppressed": row.aggregate_count < threshold,
                "submitted_at": row.submitted_at,
            }
            for row in rows
        ]
    if resource in {"facilities", "hospitals"}:
        rows = list(
            (
                await session.execute(
                    select(Tenant)
                    .where(Tenant.status == "ACTIVE")
                    .order_by(Tenant.name)
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "location": row.state_location,
                "status": row.status,
            }
            for row in rows
        ]
    if resource == "settings":
        return {
            "jurisdiction": prefix,
            "identifiable_reporting_allowed": scope.identifiable_reporting_allowed,
        }
    raise HTTPException(status_code=404, detail="Government resource not found")


@router.post("/moh/reports", status_code=201)
async def submit_disease_report(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    account = await require_account(request, session)
    if account.role in {"government", "moh"}:
        raise HTTPException(
            status_code=403,
            detail="Reports must be submitted by an authorized facility",
        )
    payload = await request.json()
    identifiable = payload.get("identifiable_payload")
    legal_reference = (
        str(payload.get("legal_authority_reference") or "").strip() or None
    )
    if identifiable and not legal_reference:
        raise HTTPException(
            status_code=422,
            detail="Identifiable reporting requires a legal authority reference",
        )
    row = MandatoryDiseaseReport(
        facility_id=account.tenant_id,
        jurisdiction_code=str(payload.get("jurisdiction_code") or "").strip(),
        report_type=str(payload.get("report_type") or "").strip(),
        condition_code=str(payload.get("condition_code") or "").strip(),
        reporting_period=str(payload.get("reporting_period") or "").strip(),
        aggregate_count=max(0, int(payload.get("aggregate_count") or 0)),
        identifiable_payload_json=json.dumps(identifiable) if identifiable else None,
        legal_authority_reference=legal_reference,
        submitted_by_id=account.id,
    )
    if not all(
        (
            row.jurisdiction_code,
            row.report_type,
            row.condition_code,
            row.reporting_period,
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Jurisdiction, report type, condition code, and reporting period are required",
        )
    session.add(row)
    await session.commit()
    return {
        "id": str(row.id),
        "status": "SUBMITTED",
        "contains_identifiable_data": bool(identifiable),
    }


@router.get("/moh/reports/{report_id}/identifiable")
async def read_identifiable_report(
    report_id: str,
    request: Request,
    legal_basis: str,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    account = await require_account(request, session)
    row = await session.get(MandatoryDiseaseReport, parse_uuid(report_id, "report_id"))
    scope = await government_scope(
        session, account, row.jurisdiction_code if row else None
    )
    if not row or not row.identifiable_payload_json:
        raise HTTPException(status_code=404, detail="Identifiable report not found")
    if (
        not scope.identifiable_reporting_allowed
        or not row.legal_authority_reference
        or len(legal_basis.strip()) < 5
    ):
        raise HTTPException(
            status_code=403,
            detail="Configured legal authority and an access basis are required",
        )
    disclosure = DataDisclosure(
        government_user_id=account.id,
        report_id=row.id,
        disclosure_type="MANDATORY_DISEASE_REPORT",
        legal_basis=legal_basis.strip(),
        fields_json=json.dumps(list(json.loads(row.identifiable_payload_json).keys())),
    )
    session.add(disclosure)
    await session.commit()
    return {
        "id": str(row.id),
        "payload": json.loads(row.identifiable_payload_json),
        "disclosure_id": str(disclosure.id),
    }
