from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

from app.schemas.domain import WebSocketEvent


class TenantConnectionManager:
    """Small in-process broadcaster.

    Production deployments can swap the internals for Redis Pub/Sub without
    changing route handlers. For a clinic LAN MVP, this keeps queue boards and
    waiting-room displays live from one Uvicorn process.
    """

    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._specialist_connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._queue_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, tenant_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[tenant_id].add(websocket)

    def disconnect(self, tenant_id: UUID, websocket: WebSocket) -> None:
        self._connections[tenant_id].discard(websocket)

    async def broadcast(self, event: WebSocketEvent) -> None:
        stale: list[WebSocket] = []
        for websocket in self._connections[event.tenant_id]:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(event.tenant_id, websocket)

    async def connect_specialist(self, specialist_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._specialist_connections[specialist_id].add(websocket)

    def disconnect_specialist(self, specialist_id: UUID, websocket: WebSocket) -> None:
        self._specialist_connections[specialist_id].discard(websocket)

    async def broadcast_specialist(self, specialist_id: UUID, payload: dict[str, object]) -> None:
        for websocket in list(self._specialist_connections[specialist_id]):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                self.disconnect_specialist(specialist_id, websocket)

    async def connect_queue(self, card_number: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._queue_connections[card_number].add(websocket)

    def disconnect_queue(self, card_number: str, websocket: WebSocket) -> None:
        self._queue_connections[card_number].discard(websocket)

    async def broadcast_queue(self, card_number: str, payload: dict[str, object]) -> None:
        for websocket in list(self._queue_connections[card_number]):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                self.disconnect_queue(card_number, websocket)


connection_manager = TenantConnectionManager()
