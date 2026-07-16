import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.services.redis_service import RedisInfrastructure


def test_disabled_redis_cache_and_rate_limit_degrade_locally() -> None:
    infrastructure = RedisInfrastructure(enabled=False, url="redis://unused", key_prefix="test")

    async def scenario() -> None:
        await infrastructure.set_json("clinical:config", {"mode": "safe"}, ttl_seconds=60)
        assert await infrastructure.get_json("clinical:config") == {"mode": "safe"}
        assert await infrastructure.allow("login", "client-1", limit=2)
        assert await infrastructure.allow("login", "client-1", limit=2)
        assert not await infrastructure.allow("login", "client-1", limit=2)
        await infrastructure.publish("tenant-1", {"type": "test"})
        await infrastructure.close()

    asyncio.run(scenario())
    assert infrastructure.available is False


def test_login_rate_limit_returns_retry_after() -> None:
    with TestClient(app) as client:
        responses = [
            client.post("/api/v1/auth/patient/login", json={"phone": "+2348000000000", "password": "wrong"})
            for _ in range(11)
        ]

    assert responses[9].status_code == 401
    assert responses[10].status_code == 429
    assert responses[10].headers["retry-after"] == "60"


def test_health_reports_dependency_degraded_modes() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["dependencies"]["redis"] == "degraded-local"
