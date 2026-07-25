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

    assert {"tenants", "staff", "auth_accounts", "auth_sessions", "tickets", "audit_logs", "demo_requests", "providers", "provider_slots", "appointments", "client_mutations", "hospital_doctor_memberships", "notifications"} <= tables
    assert revision == ("20260716_0012",)
    with sqlite3.connect(database) as connection:
        ticket_columns = {row[1] for row in connection.execute("PRAGMA table_info(tickets)")}
        tenant_columns = {row[1] for row in connection.execute("PRAGMA table_info(tenants)")}
        provider_columns = {row[1] for row in connection.execute("PRAGMA table_info(providers)")}
        appointment_columns = {row[1] for row in connection.execute("PRAGMA table_info(appointments)")}
    assert {"raw_intake_text", "extracted_symptoms", "patient_latitude", "patient_longitude", "routed_tenant_id", "route_distance_km"} <= ticket_columns
    assert {"latitude", "longitude", "accepts_patients"} <= tenant_columns
    assert {"doctor_id", "max_daily_capacity"} <= provider_columns
    assert {"hospital_id", "doctor_id", "specialty_id", "urgency", "starts_at", "ends_at"} <= appointment_columns


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
    assert sql.count("CREATE POLICY tenant_isolation_policy") == 14
    assert "WITH CHECK" in sql
    assert 'DROP POLICY IF EXISTS tenant_isolation_policy ON "tickets"' in sql
    assert "OR routed_tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid" in sql
