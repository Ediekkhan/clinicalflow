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

    assert {"tenants", "staff", "auth_accounts", "auth_sessions", "tickets", "audit_logs", "demo_requests", "providers", "provider_slots", "appointments", "client_mutations"} <= tables
    assert revision == ("20260716_0010",)
    with sqlite3.connect(database) as connection:
        ticket_columns = {row[1] for row in connection.execute("PRAGMA table_info(tickets)")}
    assert {"raw_intake_text", "extracted_symptoms"} <= ticket_columns


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
    assert sql.count("CREATE POLICY tenant_isolation_policy") == 13
    assert "WITH CHECK" in sql
