import os
import sqlite3
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def alembic_env(database_url: str) -> dict[str, str]:
    return {**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": str(BACKEND_ROOT)}


def test_initial_migration_builds_clean_sqlite_schema(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=alembic_env(f"sqlite+aiosqlite:///{database}"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()

    assert {"tenants", "staff", "auth_accounts", "auth_sessions", "tickets", "audit_logs", "demo_requests", "providers", "provider_slots", "appointments", "client_mutations", "hospital_doctor_memberships", "staff_memberships", "staff_invitations", "hospital_departments", "provider_availability", "notifications", "signup_applications", "organization_applications", "professional_credentials", "verification_documents", "consent_records", "application_review_history", "verification_events", "notification_deliveries", "care_team_assignments", "break_glass_grants", "specialties", "clinical_privileges"} <= tables
    assert {"patient_registry", "patient_facility_identities", "provider_registry", "facility_registry", "facility_services", "payer_plan_registry", "patient_consent_directives", "provenance_records", "health_card_credentials", "routing_decisions", "routing_candidates", "appointment_assignment_requests", "outbox_events", "referrals", "transfer_requests", "encounters", "care_teams", "care_team_members", "clinical_notes", "condition_records", "allergy_records", "medication_history", "procedure_records", "clinical_observations", "care_plans", "clinical_tasks", "clinical_documents", "laboratory_orders", "ordered_tests", "specimens", "accessions", "specimen_collections", "specimen_custody_events", "laboratory_results", "diagnostic_reports", "quality_control_reviews", "result_corrections", "critical_result_acknowledgements"} <= tables
    assert {"medications", "prescriptions", "prescription_items", "pharmacy_orders", "inventory_items", "stock_movements", "dispense_events", "substitution_requests", "interaction_alerts", "controlled_medication_logs", "pharmacy_deliveries", "patient_counselling", "payer_organizations", "health_plans", "member_coverages", "benefits", "provider_contracts", "eligibility_requests", "eligibility_responses", "prior_authorizations", "insurance_claims", "claim_items", "claim_responses", "denial_reasons", "claim_appeals", "remittances", "payment_reconciliations", "government_authorities", "government_user_scopes", "mandatory_disease_reports", "surveillance_aggregates", "national_indicators", "outbreak_alerts", "data_disclosures", "support_access_requests", "support_access_approvals", "country_packs", "interoperability_mappings", "offline_clinical_mutations"} <= tables
    assert {"terminology_releases", "clinical_concepts", "concept_designations", "clinical_relationships", "clinical_content_reviews"} <= tables
    assert revision == ("20260728_0026",)
    with sqlite3.connect(database) as connection:
        ticket_columns = {row[1] for row in connection.execute("PRAGMA table_info(tickets)")}
        tenant_columns = {row[1] for row in connection.execute("PRAGMA table_info(tenants)")}
        provider_columns = {row[1] for row in connection.execute("PRAGMA table_info(providers)")}
        appointment_columns = {row[1] for row in connection.execute("PRAGMA table_info(appointments)")}
        membership_columns = {row[1] for row in connection.execute("PRAGMA table_info(staff_memberships)")}
        notification_columns = {row[1] for row in connection.execute("PRAGMA table_info(notifications)")}
        department_columns = {row[1] for row in connection.execute("PRAGMA table_info(hospital_departments)")}
        availability_columns = {row[1] for row in connection.execute("PRAGMA table_info(provider_availability)")}
        invitation_columns = {row[1] for row in connection.execute("PRAGMA table_info(staff_invitations)")}
    assert {"raw_intake_text", "extracted_symptoms", "patient_latitude", "patient_longitude", "routed_tenant_id", "route_distance_km", "terminology_release_id"} <= ticket_columns
    assert {"latitude", "longitude", "accepts_patients"} <= tenant_columns
    assert {"doctor_id", "max_daily_capacity"} <= provider_columns
    assert {"hospital_id", "department_id", "doctor_id", "staff_membership_id", "specialty_id", "urgency", "starts_at", "ends_at"} <= appointment_columns
    assert {"user_id", "hospital_id", "department_id", "role", "specialty_id", "verification_status", "employment_status", "is_on_duty", "daily_capacity", "department_ref_id", "specialty_ref_id", "legacy_doctor_membership_id"} <= membership_columns
    assert {"recipient_user_id", "recipient_membership_id", "hospital_id", "department_id", "priority", "read_at"} <= notification_columns
    assert {"hospital_id", "name", "code", "status", "coordinator_membership_id", "capacity"} <= department_columns
    assert {"membership_id", "hospital_id", "department_id", "starts_at", "ends_at", "status", "maximum_appointments", "booked_appointments"} <= availability_columns
    assert {"specialty_id", "employment_type"} <= invitation_columns


def test_postgresql_offline_migration_contains_rls_policies() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        env=alembic_env("postgresql+asyncpg://unused:unused@localhost/unused"),
        capture_output=True,
        text=True,
        check=False,
    )
    sql = result.stdout
    assert result.returncode == 0, result.stderr
    for table in ("staff", "auth_accounts", "auth_sessions", "tickets", "audit_logs"):
        assert f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY' in sql
    assert "ALTER TABLE demo_requests ENABLE ROW LEVEL SECURITY" in sql
    for table in ("providers", "provider_slots", "appointments"):
        assert f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY' in sql
    assert "ALTER TABLE client_mutations ENABLE ROW LEVEL SECURITY" in sql
    for table in ("consultation_notes", "specialist_messages"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE operational_records ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE staff_memberships ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE staff_invitations ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE hospital_departments ENABLE ROW LEVEL SECURITY" in sql
    assert "ALTER TABLE provider_availability ENABLE ROW LEVEL SECURITY" in sql
    for table in ("signup_applications", "organization_applications", "professional_credentials", "verification_documents", "consent_records", "application_review_history", "verification_events"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    for table in ("notification_deliveries", "care_team_assignments", "break_glass_grants", "specialties", "clinical_privileges"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    for table in ("patient_registry", "patient_facility_identities", "provider_registry", "facility_registry", "facility_services", "payer_plan_registry", "patient_consent_directives", "provenance_records", "health_card_credentials"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    for table in ("routing_decisions", "routing_candidates", "appointment_assignment_requests", "outbox_events"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    for table in ("medications", "prescriptions", "pharmacy_orders", "inventory_items", "dispense_events", "payer_organizations", "member_coverages", "insurance_claims", "government_user_scopes", "mandatory_disease_reports", "support_access_requests", "country_packs", "offline_clinical_mutations"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    for table in ("terminology_releases", "clinical_concepts", "concept_designations", "clinical_relationships", "clinical_content_reviews"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql
    assert sql.count("CREATE POLICY tenant_isolation_policy") == 18
    assert "WITH CHECK" in sql
    assert 'DROP POLICY IF EXISTS tenant_isolation_policy ON "tickets"' in sql
    assert "OR routed_tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid" in sql
