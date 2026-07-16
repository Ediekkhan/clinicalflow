import asyncio

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.main import app
from app.routes import TriageConnectionManager


def login_patient(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/patient/login",
        json={"phone": "+2348012345678", "password": "Password123!"},
    )
    assert response.status_code == 200


def test_ticket_list_requires_an_authenticated_session() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/tickets",
            headers={"x-tenant-id": settings.default_tenant_id},
        )
    assert response.status_code == 401


def test_forged_tenant_header_cannot_override_session_tenant() -> None:
    with TestClient(app) as client:
        login_patient(client)
        response = client.get(
            "/api/v1/tickets",
            headers={"x-tenant-id": "22222222-2222-2222-2222-222222222222"},
        )

    assert response.status_code == 200
    assert all(row["tenant_id"] == settings.default_tenant_id for row in response.json())


def test_websocket_rejects_anonymous_connections() -> None:
    with TestClient(app) as client:
        try:
            with client.websocket_connect("/api/v1/ws/triage"):
                raise AssertionError("anonymous WebSocket was accepted")
        except WebSocketDisconnect as error:
            assert error.code == 4401


def test_websocket_accepts_authenticated_session_without_tenant_query() -> None:
    with TestClient(app) as client:
        login_patient(client)
        with client.websocket_connect("/api/v1/ws/triage") as websocket:
            websocket.send_text("ping")
            assert websocket.receive_text() == "pong"


def test_connection_manager_broadcasts_only_to_the_target_tenant() -> None:
    class FakeSocket:
        def __init__(self) -> None:
            self.events: list[dict] = []

        async def accept(self) -> None:
            return None

        async def send_json(self, event: dict) -> None:
            self.events.append(event)

    async def scenario() -> tuple[FakeSocket, FakeSocket]:
        manager = TriageConnectionManager()
        first, second = FakeSocket(), FakeSocket()
        await manager.connect("tenant-a", first)  # type: ignore[arg-type]
        await manager.connect("tenant-b", second)  # type: ignore[arg-type]
        await manager.broadcast("tenant-a", {"type": "ticket.created", "tenant_id": "tenant-a"})
        return first, second

    first, second = asyncio.run(scenario())
    assert first.events == [{"type": "ticket.created", "tenant_id": "tenant-a"}]
    assert second.events == []
