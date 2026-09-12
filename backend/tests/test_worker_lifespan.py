from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_production_lifespan_without_embedded_worker(monkeypatch, tmp_path):
    # Use an isolated database while exercising the production worker lifecycle.
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{(tmp_path / 'lifecycle.db').as_posix()}")
    monkeypatch.setattr(settings, "auto_create_schema", True)
    monkeypatch.setattr(settings, "redis_enabled", False)
    monkeypatch.setattr(settings, "neo4j_enabled", False)
    with TestClient(app):
        assert app.state.outbox_worker is None
