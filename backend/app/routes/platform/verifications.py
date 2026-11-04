from __future__ import annotations

from fastapi import APIRouter

from app.routes.helpers import *  # noqa: F403

router = APIRouter(prefix="/api/v1")


@router.post(
    "/platform/facility-verifications/{case_id}/documents/{document_id}/review"
)
async def review_verification_document(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    reviewer = await require_facility_reviewer(request, session)
    document = await session.scalar(
        select(VerificationDocument).where(
            VerificationDocument.id == document_id,
            VerificationDocument.signup_application_id
            == select(FacilityVerificationCase.signup_application_id)
            .where(FacilityVerificationCase.id == case_id)
            .scalar_subquery(),
        )
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    payload = await request.json()
    status = str(payload.get("status") or "").upper()
    if status not in {"VALID", "INVALID", "MORE_INFORMATION_REQUIRED"}:
        raise HTTPException(status_code=422, detail="Invalid document review status")
    document.verification_status = status
    await session.commit()
    return {
        "id": str(document.id),
        "status": document.verification_status,
        "reviewed_by": str(reviewer.id),
    }


@router.post("/platform/facility-verifications/{case_id}/request-information")
async def request_verification_information(
    case_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    reviewer = await require_facility_reviewer(request, session)
    case = await session.scalar(
        select(FacilityVerificationCase)
        .where(FacilityVerificationCase.id == case_id)
        .with_for_update()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Verification case not found")
    payload = await request.json()
    reason = str(
        payload.get("reason") or "Additional verification information is required"
    ).strip()
    case.status = "MORE_INFORMATION_REQUIRED"
    case.reviewer_notes = reason
    await session.commit()
    return {
        "id": str(case.id),
        "status": case.status,
        "reason": reason,
        "reviewer_id": str(reviewer.id),
    }


@router.post("/platform/facility-verifications/{case_id}/resubmit")
async def resubmit_verification(
    case_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    case = await session.scalar(
        select(FacilityVerificationCase)
        .where(FacilityVerificationCase.id == case_id)
        .with_for_update()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Verification case not found")
    if case.status != "MORE_INFORMATION_REQUIRED":
        raise HTTPException(
            status_code=409, detail="This case is not awaiting information"
        )
    case.status = "RESUBMITTED"
    await session.commit()
    return {"id": str(case.id), "status": case.status}


@router.get("/platform/signup-applications")
async def list_signup_applications(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    await require_roles(request, session, FACILITY_VERIFIER_ROLES | {"admin"})
    rows = (
        await session.execute(
            select(SignupApplication, OrganizationApplication, FacilityVerificationCase)
            .join(
                OrganizationApplication,
                OrganizationApplication.signup_application_id == SignupApplication.id,
            )
            .outerjoin(
                FacilityVerificationCase,
                FacilityVerificationCase.signup_application_id == SignupApplication.id,
            )
            .where(SignupApplication.application_type == "hospital")
            .order_by(SignupApplication.submitted_at.desc())
        )
    ).all()
    return {
        "items": [
            {
                "id": str(application.id),
                "reference": application.reference,
                "status": application.status,
                "organization_name": organization.legal_name,
                "email": application.email,
                "phone": application.phone,
                "country": application.country,
                "latitude": organization.latitude,
                "longitude": organization.longitude,
                "submitted_at": application.submitted_at,
                "verification_case_id": str(case.id) if case else None,
                "verification_status": case.status if case else application.status,
                "review_due_at": case.review_due_at if case else None,
            }
            for application, organization, case in rows
        ]
    }


@router.get("/platform/facility-verifications")
async def list_facility_verifications(
    request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    # Platform administrators may monitor the queue, but only dedicated
    # verification roles may assign, approve, reject, or request information.
    reviewer = await require_roles(
        request, session, FACILITY_VERIFIER_ROLES | {"admin"}
    )
    statement = (
        select(FacilityVerificationCase, SignupApplication, OrganizationApplication)
        .join(
            SignupApplication,
            SignupApplication.id == FacilityVerificationCase.signup_application_id,
        )
        .join(
            OrganizationApplication,
            OrganizationApplication.id
            == FacilityVerificationCase.organization_application_id,
        )
    )
    if reviewer.role == "facility_verifier":
        statement = statement.where(
            or_(
                FacilityVerificationCase.assigned_reviewer_id == reviewer.id,
                FacilityVerificationCase.assigned_reviewer_id.is_(None),
            )
        )
    rows = (
        await session.execute(
            statement.order_by(FacilityVerificationCase.review_due_at.asc())
        )
    ).all()
    return {
        "items": [
            {
                "id": str(case.id),
                "application_id": str(application.id),
                "reference": application.reference,
                "status": case.status,
                "priority": case.priority,
                "organization_name": organization.legal_name,
                "country": application.country,
                "review_due_at": case.review_due_at,
                "assigned_reviewer_id": (
                    str(case.assigned_reviewer_id)
                    if case.assigned_reviewer_id
                    else None
                ),
                "government_check_status": case.government_check_status,
            }
            for case, application, organization in rows
        ]
    }


@router.get("/platform/facility-verifications/{case_id}")
async def get_facility_verification(
    case_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    await require_facility_reviewer(request, session)
    case = await session.get(FacilityVerificationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Verification case not found")
    application = await session.get(SignupApplication, case.signup_application_id)
    organization = await session.get(
        OrganizationApplication, case.organization_application_id
    )
    documents = (
        await session.scalars(
            select(VerificationDocument).where(
                VerificationDocument.signup_application_id == case.signup_application_id
            )
        )
    ).all()
    findings = (
        await session.scalars(
            select(VerificationFinding).where(
                VerificationFinding.verification_case_id == case.id
            )
        )
    ).all()
    return {
        "case": {
            "id": str(case.id),
            "status": case.status,
            "priority": case.priority,
            "review_due_at": case.review_due_at,
            "government_check_status": case.government_check_status,
            "reviewer_notes": case.reviewer_notes,
        },
        "application": {
            "id": str(application.id),
            "reference": application.reference,
            "email": application.email,
            "phone": application.phone,
            "country": application.country,
            "payload": json.loads(application.payload_json),
        },
        "organization": {
            "legal_name": organization.legal_name,
            "registration_number": organization.registration_number,
            "licence_number": organization.licence_number,
            "latitude": organization.latitude,
            "longitude": organization.longitude,
        },
        "documents": [
            {
                "id": str(document.id),
                "type": document.document_type,
                "name": document.original_name,
                "status": document.verification_status,
            }
            for document in documents
        ],
        "findings": [
            {
                "id": str(finding.id),
                "type": finding.category,
                "severity": finding.severity,
                "status": finding.status,
                "description": finding.description,
            }
            for finding in findings
        ],
    }


@router.post("/platform/facility-verifications/{case_id}/assign")
async def assign_facility_verification(
    case_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    reviewer = await require_facility_reviewer(request, session)
    case = await session.scalar(
        select(FacilityVerificationCase)
        .where(FacilityVerificationCase.id == case_id)
        .with_for_update()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Verification case not found")
    if case.assigned_reviewer_id and case.assigned_reviewer_id != reviewer.id:
        raise HTTPException(status_code=409, detail="Case is already assigned")
    case.assigned_reviewer_id = reviewer.id
    if case.status == "REGISTRY_CHECK_PENDING":
        case.status = "UNDER_REVIEW"
    await session.commit()
    return {
        "id": str(case.id),
        "assigned_reviewer_id": str(reviewer.id),
        "status": case.status,
    }


@router.post("/platform/facility-verifications/{case_id}/findings")
async def create_verification_finding(
    case_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    reviewer = await require_facility_reviewer(request, session)
    case = await session.get(FacilityVerificationCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Verification case not found")
    payload = await request.json()
    finding = VerificationFinding(
        verification_case_id=case.id,
        category=str(payload.get("finding_type") or payload.get("category") or "OTHER"),
        severity=str(payload.get("severity") or "WARNING"),
        description=str(payload.get("description") or ""),
        created_by_id=reviewer.id,
    )
    session.add(finding)
    await session.commit()
    return {"id": str(finding.id), "status": finding.status}


@router.patch("/platform/signup-applications/{application_id}/review")
async def review_signup_application(
    application_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    reviewer = await require_facility_reviewer(request, session)
    payload = await request.json()
    decision = str(payload.get("decision") or "").upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(
            status_code=422, detail="Decision must be APPROVE or REJECT"
        )
    application = await session.scalar(
        select(SignupApplication)
        .where(SignupApplication.id == application_id)
        .with_for_update()
    )
    if not application or application.application_type not in ORGANIZATION_SIGNUP_TYPES:
        raise HTTPException(
            status_code=404, detail="Organization application not found"
        )
    organization = await session.scalar(
        select(OrganizationApplication)
        .where(OrganizationApplication.signup_application_id == application.id)
        .with_for_update()
    )
    if not organization:
        raise HTTPException(
            status_code=422, detail="Organization verification record is missing"
        )
    previous_status = application.status
    if decision == "REJECT":
        application.status = "REJECTED"
        organization.verification_status = "REJECTED"
        session.add(
            ApplicationReviewHistory(
                signup_application_id=application.id,
                reviewer_account_id=reviewer.id,
                previous_status=previous_status,
                new_status=application.status,
                internal_notes=str(payload.get("reason") or "") or None,
            )
        )
        await session.commit()
        return {
            "id": str(application.id),
            "status": application.status,
            "tenant_id": None,
            "admin_account_id": None,
        }
    if application.status == "ACTIVE" and application.account_id:
        admin = await session.get(AuthAccount, application.account_id)
        return {
            "id": str(application.id),
            "status": application.status,
            "tenant_id": str(admin.tenant_id) if admin else None,
            "admin_account_id": str(application.account_id),
        }
    data = json.loads(application.payload_json).get("data", {})
    admin_email = (
        str(data.get("official_email") or application.email or "").strip().lower()
    )
    if not admin_email or not application.password_hash:
        raise HTTPException(
            status_code=422,
            detail="Approved organizations require administrator email and password",
        )
    existing = await session.scalar(
        select(AuthAccount).where(func.lower(AuthAccount.identifier) == admin_email)
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Administrator account already exists"
        )
    tenant = Tenant(
        name=organization.legal_name,
        state_location=str(
            data.get("jurisdiction") or data.get("state") or application.country
        ),
        latitude=organization.latitude,
        longitude=organization.longitude,
        accepts_patients=False,
        status="VERIFIED_PENDING_SETUP",
    )
    session.add(tenant)
    await session.flush()
    facility = await ensure_facility_registry(session, tenant)
    facility.facility_type = {
        "clinic": "CLINIC",
        "pharmacy": "PHARMACY",
        "laboratory": "LABORATORY",
        "hmo": "PAYER",
        "government": "GOVERNMENT",
    }.get(application.application_type, "HOSPITAL")
    facility.country = application.country
    facility.jurisdiction = tenant.state_location
    facility.status = "VERIFIED_PENDING_SETUP"
    facility.accepts_patients = False
    department_name = (
        str(payload.get("default_department") or "Administration").strip()
        or "Administration"
    )
    department = HospitalDepartment(
        hospital_id=tenant.id,
        name=department_name,
        code=f"ADMIN-{tenant.id.hex[:8].upper()}",
        status="ACTIVE",
    )
    session.add(department)
    name_parts = (
        str(
            data.get("administrator_name")
            or data.get("full_name")
            or "Facility Administrator"
        )
        .strip()
        .split(maxsplit=1)
    )
    admin_role = (
        "hospital_admin"
        if application.application_type in {"hospital", "clinic"}
        else "admin"
    )
    # The activation link, not an application-supplied password, is the only
    # way to set the initial credential. Persist a random unusable value until
    # activation because the account schema intentionally disallows NULL hashes.
    admin = AuthAccount(
        tenant_id=tenant.id,
        role=admin_role,
        identifier=admin_email,
        password_hash=hash_password(secrets.token_urlsafe(48)),
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else "",
        email=admin_email,
        is_active=False,
    )
    session.add(admin)
    await session.flush()
    membership = StaffMembership(
        user_id=admin.id,
        hospital_id=tenant.id,
        department_id=department.name,
        department_ref_id=department.id,
        role=admin_role,
        verification_status="ACTIVATION_PENDING",
        employment_status="PENDING",
        is_active=False,
        is_on_duty=False,
        active_from=utc_now(),
    )
    session.add(membership)
    application.account_id = admin.id
    activation_token = secrets.token_urlsafe(32)
    session.add(
        FacilityAdminActivation(
            verification_case_id=(
                await session.scalar(
                    select(FacilityVerificationCase.id).where(
                        FacilityVerificationCase.signup_application_id == application.id
                    )
                )
            ),
            account_id=admin.id,
            token_hash=token_hash(activation_token),
            expires_at=utc_now() + timedelta(hours=48),
            status="PENDING",
        )
    )
    application.status = "ADMIN_ACTIVATION_PENDING"
    organization.verification_status = "VERIFIED_PENDING_SETUP"
    case = await session.scalar(
        select(FacilityVerificationCase)
        .where(FacilityVerificationCase.signup_application_id == application.id)
        .with_for_update()
    )
    if case:
        case.status = "ADMIN_ACTIVATION_PENDING"
        case.resolved_by_id = reviewer.id
        case.reviewer_notes = str(payload.get("reason") or "") or None
    session.add(
        ApplicationReviewHistory(
            signup_application_id=application.id,
            reviewer_account_id=reviewer.id,
            previous_status=previous_status,
            new_status=application.status,
            internal_notes=str(payload.get("reason") or "") or None,
        )
    )
    await session.commit()
    return {
        "id": str(application.id),
        "status": application.status,
        "tenant_id": str(tenant.id),
        "admin_account_id": str(admin.id),
        "membership_id": str(membership.id),
        "activation_required": True,
        "activation_token": activation_token,
    }
