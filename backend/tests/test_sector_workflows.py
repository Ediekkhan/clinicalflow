import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import (
    AuthAccount,
    Benefit,
    ClinicalPrivilege,
    FacilityRegistry,
    GovernmentAuthority,
    GovernmentUserScope,
    HealthPlan,
    MemberCoverage,
    PayerOrganization,
    ProviderContract,
    StaffMembership,
    Tenant,
)
from app.services.auth_service import ACCESS_COOKIE, REFRESH_COOKIE, create_session, hash_password

PASSWORD = "Password123!"


async def seed_sector_case():
    suffix = uuid4().hex[:8]
    now = datetime.now(UTC)
    async with app.state.session_factory() as session:
        hospital = Tenant(name=f"Hospital {suffix}", state_location="Test", status="ACTIVE", accepts_patients=True)
        pharmacy = Tenant(name=f"Pharmacy {suffix}", state_location="Test", status="ACTIVE", accepts_patients=False)
        payer_tenant = Tenant(name=f"Payer {suffix}", state_location="Test", status="ACTIVE", accepts_patients=False)
        government_tenant = Tenant(name=f"Government {suffix}", state_location="Test", status="ACTIVE", accepts_patients=False)
        session.add_all([hospital, pharmacy, payer_tenant, government_tenant])
        await session.flush()
        session.add(FacilityRegistry(tenant_id=pharmacy.id, facility_type="PHARMACY", country="NG", status="ACTIVE", accepts_patients=False))
        patient = AuthAccount(tenant_id=hospital.id, role="patient", identifier=f"patient-{suffix}", password_hash=hash_password(PASSWORD), first_name="Patient", last_name="Person", is_active=True)
        doctor = AuthAccount(tenant_id=hospital.id, role="doctor", identifier=f"doctor-{suffix}", password_hash=hash_password(PASSWORD), first_name="Doctor", last_name="Person", is_active=True)
        pharmacist = AuthAccount(tenant_id=pharmacy.id, role="admin", identifier=f"pharmacy-{suffix}", password_hash=hash_password(PASSWORD), first_name="Pharmacy", last_name="User", is_active=True)
        payer_user = AuthAccount(tenant_id=payer_tenant.id, role="admin", identifier=f"payer-{suffix}", password_hash=hash_password(PASSWORD), first_name="Payer", last_name="User", is_active=True)
        government_user = AuthAccount(tenant_id=government_tenant.id, role="government", identifier=f"government-{suffix}", password_hash=hash_password(PASSWORD), first_name="Government", last_name="User", is_active=True)
        session.add_all([patient, doctor, pharmacist, payer_user, government_user])
        await session.flush()
        membership = StaffMembership(user_id=doctor.id, hospital_id=hospital.id, department_id="General Medicine", role="doctor", specialty_id="General Medicine", professional_license_number=f"LIC-{suffix}", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True, active_from=now - timedelta(days=1))
        session.add(membership)
        await session.flush()
        session.add(ClinicalPrivilege(membership_id=membership.id, code="PRESCRIBE", status="ACTIVE", granted_by_account_id=doctor.id))
        payer = PayerOrganization(tenant_id=payer_tenant.id, country_code="NG", payer_type="HMO", legal_name=f"Payer {suffix}", status="ACTIVE")
        session.add(payer)
        await session.flush()
        plan = HealthPlan(payer_id=payer.id, code=f"PLAN-{suffix}", name="Test plan", currency="NGN", status="ACTIVE")
        session.add(plan)
        await session.flush()
        coverage = MemberCoverage(patient_id=patient.id, payer_id=payer.id, plan_id=plan.id, member_number=f"MEM-{suffix}", status="ACTIVE", starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=30))
        session.add_all([
            coverage,
            Benefit(plan_id=plan.id, service_code="CONSULT", coverage_percent=80, requires_authorization=False),
            ProviderContract(payer_id=payer.id, facility_id=hospital.id, status="ACTIVE", starts_at=now - timedelta(days=1)),
        ])
        authority = GovernmentAuthority(tenant_id=government_tenant.id, country_code="NG", jurisdiction_code="NG-AK", authority_level="STATE", status="ACTIVE")
        session.add(authority)
        await session.flush()
        session.add(GovernmentUserScope(user_id=government_user.id, authority_id=authority.id, jurisdiction_code="NG-AK", geographic_level="STATE", identifiable_reporting_allowed=False, status="ACTIVE"))
        tokens = {name: await create_session(session, value) for name, value in {"patient": patient, "doctor": doctor, "pharmacy": pharmacist, "payer": payer_user, "government": government_user}.items()}
        await session.commit()
        return {"hospital": hospital.id, "pharmacy": pharmacy.id, "patient": patient.id, "coverage": coverage.id, "tokens": tokens}


def use_session(client, issued):
    client.cookies.set(ACCESS_COOKIE, issued.access_token)
    client.cookies.set(REFRESH_COOKIE, issued.refresh_token)


def test_prescription_partial_dispense_is_idempotent_and_minimum_necessary():
    with TestClient(app) as client:
        case = asyncio.run(seed_sector_case())
        use_session(client, case["tokens"]["pharmacy"])
        medication = client.post("/api/v1/pharmacy/medications", json={"code": f"MED-{uuid4().hex[:6]}", "generic_name": "Test medicine"})
        assert medication.status_code == 201, medication.text
        inventory = client.post("/api/v1/pharmacy/inventory", json={"medication_id": medication.json()["id"], "batch_number": uuid4().hex, "quantity_on_hand": 20, "reorder_level": 2, "expires_at": (datetime.now(UTC) + timedelta(days=90)).isoformat()})
        assert inventory.status_code == 201, inventory.text
        use_session(client, case["tokens"]["doctor"])
        created = client.post("/api/v1/prescriptions", json={"patient_id": str(case["patient"]), "pharmacy_id": str(case["pharmacy"]), "items": [{"medication_id": medication.json()["id"], "dosage": "As directed", "frequency": "Daily", "duration_days": 5, "quantity": 10}]})
        assert created.status_code == 201, created.text
        use_session(client, case["tokens"]["pharmacy"])
        orders = client.get("/api/v1/pharmacy/prescriptions")
        assert orders.status_code == 200 and orders.json()
        assert "phone" not in str(orders.json()).lower() and "medical_history" not in str(orders.json()).lower()
        order_id = created.json()["order_id"]
        assert client.post(f"/api/v1/pharmacy/orders/{order_id}/validate", json={}).status_code == 200
        async def item_id():
            async with app.state.session_factory() as session:
                from app.models import PrescriptionItem
                return str(await session.scalar(select(PrescriptionItem.id).where(PrescriptionItem.prescription_id == UUID(created.json()["id"]))))
        prescription_item_id = asyncio.run(item_id())
        payload = {"prescription_item_id": prescription_item_id, "inventory_item_id": inventory.json()["id"], "quantity": 4}
        first = client.post(f"/api/v1/pharmacy/orders/{order_id}/dispense", json=payload, headers={"x-idempotency-key": "partial-one"})
        duplicate = client.post(f"/api/v1/pharmacy/orders/{order_id}/dispense", json=payload, headers={"x-idempotency-key": "partial-one"})
        assert first.status_code == 200 and first.json()["status"] == "PARTIALLY_DISPENSED"
        assert duplicate.status_code == 200 and duplicate.json()["status"] == "ALREADY_PROCESSED"


def test_coverage_emergency_and_duplicate_claim_controls():
    with TestClient(app) as client:
        case = asyncio.run(seed_sector_case())
        use_session(client, case["tokens"]["patient"])
        eligible = client.post("/api/v1/coverage/eligibility", json={"facility_id": str(case["hospital"]), "coverage_id": str(case["coverage"]), "service_code": "CONSULT", "lawful_basis": "CARE_DELIVERY"})
        assert eligible.status_code == 201 and eligible.json()["eligible"] is True
        emergency = client.post("/api/v1/coverage/eligibility", json={"facility_id": str(case["hospital"]), "service_code": "UNLISTED", "lawful_basis": "EMERGENCY_CARE", "emergency": True})
        assert emergency.status_code == 201 and emergency.json()["care_must_continue"] is True
        use_session(client, case["tokens"]["doctor"])
        reference = f"CLAIM-{uuid4().hex}"
        body = {"coverage_id": str(case["coverage"]), "external_reference": reference, "lawful_basis": "CLAIMS_PROCESSING", "items": [{"service_code": "CONSULT", "amount_minor": 1000, "quantity": 1}]}
        assert client.post("/api/v1/claims", json=body).status_code == 201
        assert client.post("/api/v1/claims", json=body).status_code == 409


def test_government_scope_suppresses_small_cells_and_blocks_identifiable_access():
    with TestClient(app) as client:
        case = asyncio.run(seed_sector_case())
        use_session(client, case["tokens"]["doctor"])
        report = client.post("/api/v1/moh/reports", json={"jurisdiction_code": "NG-AK:UYO", "report_type": "SURVEILLANCE", "condition_code": "TEST", "reporting_period": "2026-W30", "aggregate_count": 2, "identifiable_payload": {"patient_id": str(case["patient"])}, "legal_authority_reference": "TEST-AUTHORITY"})
        assert report.status_code == 201
        use_session(client, case["tokens"]["government"])
        rows = client.get("/api/v1/moh/reports?jurisdiction=NG-AK")
        assert rows.status_code == 200 and rows.json()[0]["suppressed"] is True and rows.json()[0]["aggregate_count"] is None
        denied = client.get(f"/api/v1/moh/reports/{report.json()['id']}/identifiable?legal_basis=Official%20review")
        assert denied.status_code == 403


def test_country_pack_and_offline_mutations_are_versioned_and_idempotent():
    with TestClient(app) as client:
        case = asyncio.run(seed_sector_case())
        use_session(client, case["tokens"]["doctor"])
        pack = client.get("/api/v1/country-packs/NG/active")
        assert pack.status_code == 200
        assert pack.json()["requires_legal_review"] is True
        mappings = client.get("/api/v1/interoperability/mappings")
        assert mappings.status_code == 200 and any(row["resource_type"] == "Patient" for row in mappings.json())
        client_id = uuid4().hex
        body = {"client_mutation_id": client_id, "mutation_type": "CLINICAL_TASK", "payload": {"patient_id": str(case["patient"]), "task_type": "FOLLOW_UP", "description": "Review after discharge"}}
        first = client.post("/api/v1/offline/mutations", json=body)
        duplicate = client.post("/api/v1/offline/mutations", json=body)
        assert first.status_code == 202 and duplicate.status_code == 202 and duplicate.json()["duplicate"] is True
        synced = client.post("/api/v1/offline/mutations/sync")
        assert synced.status_code == 200 and synced.json()["synced"] == 1
