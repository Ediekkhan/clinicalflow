from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app
from app.services.demo_seeds import _require_fixture_mode


ROOT = Path(__file__).resolve().parents[1]


def test_production_settings_reject_legacy_demo_configuration() -> None:
    with pytest.raises(ValidationError, match="Unsafe production configuration"):
        Settings(
            app_env="production",
            database_url="sqlite+aiosqlite:///unsafe.db",
            auto_create_schema=True,
            auth_cookie_secure=False,
            channel_webhook_secret="change-me",
            session_secret="development-only-change-me",
            cors_origins="http://localhost:3000",
            enable_test_fixtures=True,
            enable_demo_content=True,
            default_credentials_present=True,
        )


def test_demo_seed_functions_require_test_fixture_mode() -> None:
    previous_environment = settings.app_env
    previous_fixtures = settings.enable_test_fixtures
    try:
        settings.app_env = "production"
        settings.enable_test_fixtures = True
        with pytest.raises(RuntimeError, match="only when test fixtures are enabled"):
            _require_fixture_mode()
    finally:
        settings.app_env = previous_environment
        settings.enable_test_fixtures = previous_fixtures


def test_legacy_login_shortcuts_are_not_available_without_test_fixtures() -> None:
    previous_environment = settings.app_env
    previous_fixtures = settings.enable_test_fixtures
    try:
        settings.app_env = "development"
        settings.enable_test_fixtures = False
        with TestClient(app) as client:
            assert client.post("/api/auth/staff/pin-login", json={"role": "doctor", "pin": "0000"}).status_code == 404
            assert client.post(
                "/api/auth/hospital/account-login",
                json={"hospital_code": "test", "role": "hospital", "password": "test"},
            ).status_code == 404
    finally:
        settings.app_env = previous_environment
        settings.enable_test_fixtures = previous_fixtures


def test_normal_startup_creates_no_demo_domain_records_and_cleanup_is_dry_run(tmp_path: Path) -> None:
    database_path = tmp_path / "empty-pilot.db"
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "development",
            "ENABLE_TEST_FIXTURES": "false",
            "ENABLE_DEMO_CONTENT": "false",
            "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "AUTO_CREATE_SCHEMA": "true",
        }
    )
    script = """
import asyncio
import json
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from app.main import app
from app.models import Appointment, AuthAccount, Notification, OperationalRecord, PatientRegistry, ProviderSlot, StaffMembership, Tenant, Ticket

async def counts():
    models = (Tenant, AuthAccount, StaffMembership, PatientRegistry, ProviderSlot, Appointment, Ticket, Notification, OperationalRecord)
    async with app.state.session_factory() as session:
        return {model.__name__: int(await session.scalar(select(func.count()).select_from(model)) or 0) for model in models}

with TestClient(app):
    print(json.dumps(asyncio.run(counts()), sort_keys=True))
"""
    startup = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    counts = json.loads(startup.stdout.strip().splitlines()[-1])
    assert counts == {
        "Appointment": 0,
        "AuthAccount": 0,
        "Notification": 0,
        "OperationalRecord": 0,
        "PatientRegistry": 0,
        "ProviderSlot": 0,
        "StaffMembership": 0,
        "Tenant": 0,
        "Ticket": 0,
    }

    for command in (
        ["production", "audit-demo-data"],
        ["production", "remove-demo-data", "--dry-run"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "app.cli", *command],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout.strip())
        assert payload["records"] == []
        assert payload["dry_run_only"] is True
        if command[1] == "remove-demo-data":
            assert payload["deleted"] == 0
            assert payload["would_delete"] == 0
