import asyncio
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.main import app
from app.models import (
    AuthAccount,
    FacilityRegistry,
    FacilityService,
    PatientFacilityIdentity,
    PatientRegistry,
    ProviderRegistry,
    ProvenanceRecord,
    StaffMembership,
    Tenant,
)
from app.services.auth_service import hash_password
from app.services.registry_service import patient_duplicate_key


async def seed_registry_fixture() -> dict[str, str]:
    suffix = uuid4().hex[:8]
    facility_id = uuid4()
    second_facility_id = uuid4()
    patient_id = uuid4()
    doctor_id = uuid4()
    patient_phone = f"+23470{suffix[:6]}"
    doctor_email = f"registry-doctor-{suffix}@example.com"
    async with app.state.session_factory() as session:
        default_tenant = await session.get(Tenant, UUID(settings.default_tenant_id))
        if not default_tenant:
            raise AssertionError("Default tenant was not seeded")
        facility = Tenant(id=facility_id, name=f"Registry Facility {suffix}", state_location="Test State", latitude=5.0, longitude=7.0, accepts_patients=True, status="ACTIVE")
        second_facility = Tenant(id=second_facility_id, name=f"Second Registry Facility {suffix}", state_location="Test State", accepts_patients=True, status="ACTIVE")
        session.add_all([facility, second_facility])
        patient_account = AuthAccount(id=patient_id, tenant_id=default_tenant.id, role="patient", identifier=patient_phone, password_hash=hash_password("Password123!"), first_name="Registry", last_name=suffix, phone=patient_phone, card_number=f"SV-{suffix.upper()}", is_active=True)
        doctor = AuthAccount(id=doctor_id, tenant_id=default_tenant.id, role="specialist", identifier=doctor_email, password_hash=hash_password("Password123!"), first_name="Registry", last_name="Clinician", email=doctor_email, specialty="Cardiology", is_active=True)
        session.add_all([patient_account, doctor])
        await session.flush()
        patient = PatientRegistry(account_id=patient_id, internal_identifier=f"PT-{suffix.upper()}", country="NG", first_name="Registry", last_name=suffix, phone=patient_phone, duplicate_key=patient_duplicate_key("Registry", suffix, None))
        facility_registry = FacilityRegistry(tenant_id=facility_id, facility_type="HOSPITAL", country="NG", jurisdiction="Test State", emergency_capable=True, status="ACTIVE", accepts_patients=True)
        session.add_all([patient, facility_registry])
        await session.flush()
        session.add_all([
            PatientFacilityIdentity(patient_id=patient.id, facility_id=facility_id, local_card_number=f"A-{suffix}"),
            PatientFacilityIdentity(patient_id=patient.id, facility_id=second_facility_id, local_card_number=f"B-{suffix}"),
            FacilityService(facility_registry_id=facility_registry.id, service_code="EMERGENCY", specialty_code="CARDIOLOGY", status="ACTIVE", available_capacity=3),
            ProviderRegistry(account_id=doctor_id, practitioner_identifier=f"PR-{suffix.upper()}", professional_role="SPECIALIST", licence_jurisdiction="NG", licence_number=f"LIC-{suffix}", verification_status="VERIFIED"),
            StaffMembership(user_id=doctor_id, hospital_id=default_tenant.id, department_id="Cardiology", role="specialist", specialty_id="Cardiology", verification_status="VERIFIED", employment_status="ACTIVE", is_active=True, is_on_duty=True),
        ])
        await session.commit()
    return {"facility_id": str(facility_id), "patient_id": str(patient_id), "patient_phone": patient_phone, "doctor_id": str(doctor_id), "doctor_email": doctor_email, "facility_name": facility.name}


def test_duplicate_key_does_not_use_phone_as_patient_identity() -> None:
    first = patient_duplicate_key("  Registry ", "Patient", "2000-01-01", "NG")
    same_identity = patient_duplicate_key("registry", "patient", "2000-01-01", "ng")
    different_birth_date = patient_duplicate_key("Registry", "Patient", "2001-01-01", "NG")
    assert first == same_identity
    assert first != different_birth_date


def test_patient_can_have_multiple_facility_identifiers() -> None:
    with TestClient(app):
        seeded = asyncio.run(seed_registry_fixture())

    async def count_identities() -> int:
        async with app.state.session_factory() as session:
            patient = await session.scalar(select(PatientRegistry).where(PatientRegistry.account_id == UUID(seeded["patient_id"])))
            rows = (await session.execute(select(PatientFacilityIdentity).where(PatientFacilityIdentity.patient_id == patient.id))).scalars().all()
            return len(rows)

    assert asyncio.run(count_identities()) == 2


def test_facility_capability_search_and_provider_licence_status() -> None:
    with TestClient(app) as client:
        seeded = asyncio.run(seed_registry_fixture())
        facilities = client.get("/api/v1/registry/facilities?service_code=EMERGENCY&specialty_code=CARDIOLOGY&emergency_capable=true")
        assert client.post("/api/v1/auth/specialist/login", json={"email": seeded["doctor_email"], "password": "Password123!"}).status_code == 200
        provider = client.get(f"/api/v1/registry/providers/{seeded['doctor_id']}")

    assert facilities.status_code == 200
    assert seeded["facility_name"] in {item["name"] for item in facilities.json()["items"]}
    assert provider.status_code == 200
    assert provider.json()["verification_status"] == "VERIFIED"


def test_secure_qr_lookup_and_consent_enforcement() -> None:
    with TestClient(app) as client:
        seeded = asyncio.run(seed_registry_fixture())
        assert client.post("/api/v1/auth/patient/login", json={"phone": seeded["patient_phone"], "password": "Password123!"}).status_code == 200
        card = client.get("/api/v1/patient/health-card")
        payload = card.json()["qr_payload"]
        assert "Registry" not in payload
        assert seeded["patient_phone"] not in payload
        assert client.patch("/api/v1/patient/consents/CARE_DELIVERY", json={"status": "ACTIVE", "data_categories": ["identity"]}).status_code == 200
        client.post("/api/v1/auth/logout")
        assert client.post("/api/v1/auth/specialist/login", json={"email": seeded["doctor_email"], "password": "Password123!"}).status_code == 200
        allowed = client.post("/api/v1/health-card/lookup", json={"token": payload})
        client.post("/api/v1/auth/logout")
        assert client.post("/api/v1/auth/patient/login", json={"phone": seeded["patient_phone"], "password": "Password123!"}).status_code == 200
        assert client.patch("/api/v1/patient/consents/CARE_DELIVERY", json={"status": "WITHDRAWN"}).status_code == 200
        client.post("/api/v1/auth/logout")
        assert client.post("/api/v1/auth/specialist/login", json={"email": seeded["doctor_email"], "password": "Password123!"}).status_code == 200
        denied = client.post("/api/v1/health-card/lookup", json={"token": payload})

    assert card.status_code == 200
    assert allowed.status_code == 200
    assert denied.status_code == 403

    async def lookup_audit_count() -> int:
        async with app.state.session_factory() as session:
            rows = (await session.execute(select(ProvenanceRecord).where(ProvenanceRecord.action.in_(["LOOKED_UP", "ACCESS_DENIED_CONSENT"])))).scalars().all()
            return len(rows)

    assert asyncio.run(lookup_audit_count()) >= 2




