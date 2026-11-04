import importlib
import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_database_url_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test_override.db")
    import app.config as config_module

    importlib.reload(config_module)

    assert config_module.settings.database_url.endswith("test_override.db")
    assert config_module.settings.database_url.startswith("sqlite+aiosqlite:///")


def test_hosted_postgres_url_is_normalized_for_asyncpg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.neon.tech/app?sslmode=require")
    import app.config as config_module

    importlib.reload(config_module)

    assert config_module.settings.database_url == "postgresql+asyncpg://user:pass@example.neon.tech/app?ssl=require"


def production_settings(**overrides):
    from app.config import Settings

    values = {
        "app_env": "production",
        "app_environment": "production",
        "enable_test_fixtures": False,
        "enable_demo_content": False,
        "default_credentials_present": False,
        "database_url": "postgresql://clinicalflow:password@db.example.com/clinicalflow",
        "auto_create_schema": False,
        "auth_cookie_secure": True,
        "skip_phone_verification": False,
        "channel_webhook_secret": "w" * 32,
        "session_secret": "s" * 32,
        "platform_tenant_id": "54fbd0a7-c59b-4c3d-b3ba-66320e69e25d",
        "cors_origins": "https://app.clinicalflow.example",
    }
    values.update(overrides)
    return Settings(**values)


def test_approved_production_configuration_is_accepted() -> None:
    settings = production_settings()

    assert settings.environment == "production"
    assert settings.operational_tenant_id == "54fbd0a7-c59b-4c3d-b3ba-66320e69e25d"
    assert settings.allowed_origins == ["https://app.clinicalflow.example"]


@pytest.mark.parametrize(
    ("override", "expected_error"),
    [
        ({"skip_phone_verification": True}, "phone verification must not be skipped"),
        ({"platform_tenant_id": None}, "PLATFORM_TENANT_ID must be a non-demo UUID"),
        ({"platform_tenant_id": "11111111-1111-1111-1111-111111111111"}, "PLATFORM_TENANT_ID must be a non-demo UUID"),
        ({"cors_origins": "http://app.clinicalflow.example"}, "CORS_ORIGINS must contain only exact HTTPS origins"),
        ({"cors_origins": "https://app.clinicalflow.example/path"}, "CORS_ORIGINS must contain only exact HTTPS origins"),
        ({"cors_origins": "*"}, "CORS_ORIGINS must contain only exact HTTPS origins"),
        ({"session_secret": "short"}, "SESSION_SECRET must contain at least 32 characters"),
        ({"channel_webhook_secret": "change-me"}, "CHANNEL_WEBHOOK_SECRET must contain at least 32 characters"),
    ],
)
def test_unsafe_production_values_fail_closed(override, expected_error) -> None:
    with pytest.raises(ValidationError, match=expected_error):
        production_settings(**override)


def test_configuration_errors_do_not_expose_secret_values() -> None:
    exposed_secret = "private-value"

    with pytest.raises(ValidationError) as error:
        production_settings(session_secret=exposed_secret, channel_webhook_secret=exposed_secret)

    assert exposed_secret not in str(error.value)
