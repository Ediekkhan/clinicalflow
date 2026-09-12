import pytest
from pydantic import ValidationError

from app.config import Settings


def production_settings(origin):
    return Settings(_env_file=None, app_env="production", database_url="postgresql+asyncpg://user:password@db.invalid/app",
                    auto_create_schema=False, auth_cookie_secure=True,
                    channel_webhook_secret="test-webhook-secret", session_secret="s" * 40,
                    default_tenant_id="22222222-2222-2222-2222-222222222222",
                    enable_test_fixtures=False, enable_demo_content=False, cors_origins=origin)


@pytest.mark.parametrize("origin", ["*", "https://*.example.org", "http://example.org", "https://example.org/path",
    "https://user:password@example.org", "https://example.org?x=1", "https://[::1]", "https://example.org:invalid"])
def test_unsafe_production_origins_rejected(origin):
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        production_settings(origin)


def test_explicit_https_origins_supported():
    config = production_settings("https://app.example.org,https://admin.example.org:8443/")
    assert config.allowed_origins == ["https://app.example.org", "https://admin.example.org:8443"]
