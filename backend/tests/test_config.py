import importlib
import os
import sys
from pathlib import Path

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
