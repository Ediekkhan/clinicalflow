"""Add canonical healthcare registries and secure health-card credentials.

Revision ID: 20260728_0019
Revises: 20260728_0018
"""
from collections.abc import Sequence
from datetime import UTC, datetime
import hashlib
import json
import re
import uuid

from alembic import context, op
import sqlalchemy as sa

revision: str = "20260728_0019"
down_revision: str | None = "20260728_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _identity_key(first_name: str, last_name: str, date_of_birth: object, country: str) -> str:
    name = re.sub(r"\s+", " ", f"{first_name} {last_name}".strip().casefold())
    raw = f"{name}|{date_of_birth or ''}|{country.upper()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def upgrade() -> None:
    op.create_table(
        "patient_registry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("internal_identifier", sa.String(64), nullable=False),
        sa.Column("country", sa.String(128), nullable=False, server_default="NG"),
        sa.Column("national_identifier_hash", sa.String(128)),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("last_name", sa.String(128), nullable=False),
        sa.Column("date_of_birth", sa.DateTime(timezone=True)),
        sa.Column("sex_at_birth", sa.String(32)),
        sa.Column("gender_identity", sa.String(64)),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(255)),
        sa.Column("address_json", sa.Text()),
        sa.Column("emergency_contact_json", sa.Text()),
        sa.Column("preferred_language", sa.String(32), nullable=False, server_default="en"),
        sa.Column("duplicate_key", sa.String(128), nullable=False),
        sa.Column("duplicate_review_status", sa.String(32), nullable=False, server_default="CLEAR"),
        sa.Column("is_deceased", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deceased_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", name="uq_patient_registry_account"),
        sa.UniqueConstraint("internal_identifier", name="uq_patient_registry_internal_identifier"),
    )
    op.create_index("ix_patient_registry_duplicate_key", "patient_registry", ["duplicate_key"])
    op.create_index("ix_patient_registry_national_identifier_hash", "patient_registry", ["national_identifier_hash"])
    op.create_index("ix_patient_registry_phone", "patient_registry", ["phone"])
    op.create_index("ix_patient_registry_email", "patient_registry", ["email"])
    op.create_table(
        "patient_facility_identities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patient_registry.id"), nullable=False),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("local_card_number", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("patient_id", "facility_id", name="uq_patient_facility_identity"),
    )
    op.create_index("ix_patient_facility_identities_patient_id", "patient_facility_identities", ["patient_id"])
    op.create_index("ix_patient_facility_identities_facility_id", "patient_facility_identities", ["facility_id"])
    op.create_table(
        "provider_registry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id"), nullable=False),
        sa.Column("practitioner_identifier", sa.String(64), nullable=False),
        sa.Column("professional_role", sa.String(64), nullable=False),
        sa.Column("licence_jurisdiction", sa.String(128)),
        sa.Column("licence_number", sa.String(128)),
        sa.Column("specialty_id", sa.Uuid(), sa.ForeignKey("specialties.id")),
        sa.Column("verification_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", name="uq_provider_registry_account"),
        sa.UniqueConstraint("practitioner_identifier"),
    )
    op.create_index("ix_provider_registry_licence", "provider_registry", ["licence_jurisdiction", "licence_number"])
    op.create_table(
        "facility_registry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("facility_type", sa.String(64), nullable=False, server_default="HOSPITAL"),
        sa.Column("country", sa.String(128), nullable=False, server_default="NG"),
        sa.Column("jurisdiction", sa.String(128)),
        sa.Column("opening_hours_json", sa.Text()),
        sa.Column("emergency_capable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("equipment_json", sa.Text()),
        sa.Column("age_groups_json", sa.Text()),
        sa.Column("capacity_status", sa.String(32), nullable=False, server_default="AVAILABLE"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("accepts_patients", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_facility_registry_tenant"),
    )
    op.create_index("ix_facility_registry_search", "facility_registry", ["facility_type", "country", "status", "accepts_patients"])
    op.create_table(
        "facility_services",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("facility_registry_id", sa.Uuid(), sa.ForeignKey("facility_registry.id"), nullable=False),
        sa.Column("service_code", sa.String(128), nullable=False),
        sa.Column("specialty_code", sa.String(128)),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("available_capacity", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("facility_registry_id", "service_code", "specialty_code", name="uq_facility_service_capability"),
    )
    op.create_index("ix_facility_services_search", "facility_services", ["service_code", "specialty_code", "status"])
    op.create_table(
        "payer_plan_registry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("payer_type", sa.String(64), nullable=False),
        sa.Column("country", sa.String(128), nullable=False, server_default="NG"),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_payer_plan_registry_code"),
    )
    op.create_table(
        "patient_consent_directives",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patient_registry.id"), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("grantee_type", sa.String(32), nullable=False, server_default="CARE_TEAM"),
        sa.Column("grantee_id", sa.Uuid()),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("data_categories_json", sa.Text()),
        sa.Column("policy_version", sa.String(32), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("patient_id", "purpose", "grantee_type", "grantee_id", name="uq_patient_consent_scope"),
    )
    op.create_index("ix_patient_consent_lookup", "patient_consent_directives", ["patient_id", "purpose", "status"])
    op.create_table(
        "provenance_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_account_id", sa.Uuid(), sa.ForeignKey("auth_accounts.id")),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_provenance_resource", "provenance_records", ["resource_type", "resource_id", "recorded_at"])
    op.create_table(
        "health_card_credentials",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patient_registry.id"), nullable=False),
        sa.Column("issuer_facility_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("card_number", sa.String(64), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("emergency_access_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("card_number"),
    )
    op.create_index("ix_health_card_token_hash", "health_card_credentials", ["token_hash"], unique=True)
    op.create_index("ix_health_card_patient_status", "health_card_credentials", ["patient_id", "status"])

    registry_tables = (
        "patient_registry", "patient_facility_identities", "provider_registry",
        "facility_registry", "facility_services", "payer_plan_registry",
        "patient_consent_directives", "provenance_records", "health_card_credentials",
    )
    if context.is_offline_mode():
        for table in registry_tables:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        return

    bind = op.get_bind()
    now = datetime.now(UTC)
    tenants = list(bind.execute(sa.text("SELECT id, state_location, status, accepts_patients FROM tenants")).mappings())
    for tenant in tenants:
        bind.execute(
            sa.text(
                "INSERT INTO facility_registry "
                "(id, tenant_id, facility_type, country, jurisdiction, emergency_capable, capacity_status, status, accepts_patients, created_at) "
                "VALUES (:id, :tenant_id, 'HOSPITAL', 'NG', :jurisdiction, 0, 'AVAILABLE', :status, :accepts, :created_at)"
            ),
            {"id": uuid.uuid4(), "tenant_id": tenant["id"], "jurisdiction": tenant["state_location"], "status": tenant["status"], "accepts": tenant["accepts_patients"], "created_at": now},
        )
    accounts = list(bind.execute(sa.text("SELECT id, tenant_id, role, first_name, last_name, phone, email, card_number, date_of_birth, gender, state, lga, emergency_contact, specialty FROM auth_accounts")).mappings())
    for account in accounts:
        role = str(account["role"]).lower()
        if role == "patient":
            patient_id = uuid.uuid4()
            internal_id = f"PT-{str(account['id']).replace('-', '')[:16].upper()}"
            bind.execute(
                sa.text(
                    "INSERT INTO patient_registry "
                    "(id, account_id, internal_identifier, country, first_name, last_name, date_of_birth, sex_at_birth, gender_identity, phone, email, address_json, emergency_contact_json, preferred_language, duplicate_key, duplicate_review_status, is_deceased, created_at, updated_at) "
                    "VALUES (:id, :account_id, :internal, 'NG', :first_name, :last_name, :dob, :gender, :gender, :phone, :email, :address, :emergency, 'en', :duplicate_key, 'CLEAR', 0, :created_at, :updated_at)"
                ),
                {
                    "id": patient_id, "account_id": account["id"], "internal": internal_id,
                    "first_name": account["first_name"], "last_name": account["last_name"],
                    "dob": account["date_of_birth"], "gender": account["gender"],
                    "phone": account["phone"], "email": account["email"],
                    "address": json.dumps({"state": account["state"], "lga": account["lga"]}),
                    "emergency": json.dumps({"phone": account["emergency_contact"]}),
                    "duplicate_key": _identity_key(account["first_name"], account["last_name"], account["date_of_birth"], "NG"),
                    "created_at": now, "updated_at": now,
                },
            )
            bind.execute(
                sa.text(
                    "INSERT INTO patient_consent_directives "
                    "(id, patient_id, purpose, grantee_type, status, policy_version, granted_at) "
                    "VALUES (:id, :patient_id, 'CARE_DELIVERY', 'CARE_TEAM', 'ACTIVE', '2026-07', :granted_at)"
                ),
                {"id": uuid.uuid4(), "patient_id": patient_id, "granted_at": now},
            )
        elif role in {"specialist", "doctor", "nurse", "lab", "pharmacy"}:
            bind.execute(
                sa.text(
                    "INSERT INTO provider_registry "
                    "(id, account_id, practitioner_identifier, professional_role, specialty_id, verification_status, created_at) "
                    "VALUES (:id, :account_id, :identifier, :role, NULL, 'PENDING', :created_at)"
                ),
                {"id": uuid.uuid4(), "account_id": account["id"], "identifier": f"PR-{str(account['id']).replace('-', '')[:16].upper()}", "role": role.upper(), "created_at": now},
            )
    if bind.dialect.name == "postgresql":
        for table in registry_tables:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_health_card_patient_status", table_name="health_card_credentials")
    op.drop_index("ix_health_card_token_hash", table_name="health_card_credentials")
    op.drop_table("health_card_credentials")
    op.drop_index("ix_provenance_resource", table_name="provenance_records")
    op.drop_table("provenance_records")
    op.drop_index("ix_patient_consent_lookup", table_name="patient_consent_directives")
    op.drop_table("patient_consent_directives")
    op.drop_table("payer_plan_registry")
    op.drop_index("ix_facility_services_search", table_name="facility_services")
    op.drop_table("facility_services")
    op.drop_index("ix_facility_registry_search", table_name="facility_registry")
    op.drop_table("facility_registry")
    op.drop_index("ix_provider_registry_licence", table_name="provider_registry")
    op.drop_table("provider_registry")
    op.drop_index("ix_patient_facility_identities_facility_id", table_name="patient_facility_identities")
    op.drop_index("ix_patient_facility_identities_patient_id", table_name="patient_facility_identities")
    op.drop_table("patient_facility_identities")
    op.drop_index("ix_patient_registry_email", table_name="patient_registry")
    op.drop_index("ix_patient_registry_phone", table_name="patient_registry")
    op.drop_index("ix_patient_registry_national_identifier_hash", table_name="patient_registry")
    op.drop_index("ix_patient_registry_duplicate_key", table_name="patient_registry")
    op.drop_table("patient_registry")


