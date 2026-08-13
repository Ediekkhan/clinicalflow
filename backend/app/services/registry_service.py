from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuthAccount,
    FacilityRegistry,
    HealthCardCredential,
    PatientConsentDirective,
    PatientRegistry,
    ProvenanceRecord,
    ProviderRegistry,
    Tenant,
)
from app.services.auth_service import token_hash, utc_now


def patient_duplicate_key(first_name: str, last_name: str, date_of_birth: object, country: str = "NG") -> str:
    normalized_name = re.sub(r"\s+", " ", f"{first_name} {last_name}".strip().casefold())
    identity = f"{normalized_name}|{date_of_birth or ''}|{country.upper()}"
    return hashlib.sha256(identity.encode()).hexdigest()


async def ensure_patient_registry(
    session: AsyncSession,
    account: AuthAccount,
    *,
    country: str = "NG",
) -> PatientRegistry:
    patient = await session.scalar(select(PatientRegistry).where(PatientRegistry.account_id == account.id))
    if patient:
        return patient
    patient = PatientRegistry(
        account_id=account.id,
        internal_identifier=f"PT-{account.id.hex[:16].upper()}",
        country=country,
        first_name=account.first_name,
        last_name=account.last_name,
        date_of_birth=account.date_of_birth,
        sex_at_birth=account.gender,
        gender_identity=account.gender,
        phone=account.phone,
        email=account.email,
        address_json=json.dumps({"state": account.state, "lga": account.lga}),
        emergency_contact_json=json.dumps({"phone": account.emergency_contact}),
        duplicate_key=patient_duplicate_key(account.first_name, account.last_name, account.date_of_birth, country),
    )
    session.add(patient)
    await session.flush()
    session.add(
        PatientConsentDirective(
            patient_id=patient.id,
            purpose="CARE_DELIVERY",
            grantee_type="CARE_TEAM",
            status="ACTIVE",
            policy_version="2026-07",
        )
    )
    session.add(
        ProvenanceRecord(
            tenant_id=account.tenant_id,
            resource_type="PatientRegistry",
            resource_id=patient.id,
            action="CREATED",
            actor_account_id=account.id,
            source="ACCOUNT_MIGRATION",
        )
    )
    return patient


async def ensure_facility_registry(session: AsyncSession, tenant: Tenant) -> FacilityRegistry:
    facility = await session.scalar(select(FacilityRegistry).where(FacilityRegistry.tenant_id == tenant.id))
    if facility:
        return facility
    facility = FacilityRegistry(
        tenant_id=tenant.id,
        facility_type="HOSPITAL",
        country="NG",
        jurisdiction=tenant.state_location,
        status=tenant.status,
        accepts_patients=tenant.accepts_patients,
    )
    session.add(facility)
    await session.flush()
    return facility


async def ensure_provider_registry(session: AsyncSession, account: AuthAccount) -> ProviderRegistry:
    provider = await session.scalar(select(ProviderRegistry).where(ProviderRegistry.account_id == account.id))
    if provider:
        return provider
    provider = ProviderRegistry(
        account_id=account.id,
        practitioner_identifier=f"PR-{account.id.hex[:16].upper()}",
        professional_role=account.role.upper(),
        verification_status="PENDING",
    )
    session.add(provider)
    await session.flush()
    return provider


async def issue_health_card_credential(
    session: AsyncSession,
    account: AuthAccount,
    patient: PatientRegistry,
) -> tuple[HealthCardCredential, str]:
    now = utc_now()
    current = await session.scalar(
        select(HealthCardCredential)
        .where(HealthCardCredential.patient_id == patient.id, HealthCardCredential.status == "ACTIVE")
        .order_by(HealthCardCredential.issued_at.desc())
        .limit(1)
    )
    if current:
        current.status = "REVOKED"
        current.revoked_at = now
    raw_token = secrets.token_urlsafe(32)
    credential = HealthCardCredential(
        patient_id=patient.id,
        issuer_facility_id=account.tenant_id,
        card_number=f"{account.card_number or f'SV-{secrets.token_hex(5).upper()}'}-{secrets.token_hex(3).upper()}",
        token_hash=token_hash(raw_token),
        expires_at=now + timedelta(days=365),
        emergency_access_enabled=True,
    )
    if not account.card_number:
        account.card_number = credential.card_number.rsplit("-", 1)[0]
    session.add(credential)
    await session.flush()
    session.add(
        ProvenanceRecord(
            tenant_id=account.tenant_id,
            resource_type="HealthCardCredential",
            resource_id=credential.id,
            action="ISSUED",
            actor_account_id=account.id,
            source="PATIENT_PORTAL",
        )
    )
    return credential, raw_token

