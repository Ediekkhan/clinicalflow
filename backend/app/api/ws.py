from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import resolve_websocket_principal
from app.services.realtime import connection_manager


router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/triage")
async def triage_socket(websocket: WebSocket) -> None:
    principal = resolve_websocket_principal(websocket)
    await connection_manager.connect(principal.tenant_id, websocket)
    try:
        while True:
            # Client pings allow queue boards to detect half-open LAN connections.
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(principal.tenant_id, websocket)


@router.websocket("/specialist/{specialist_id}")
async def specialist_socket(websocket: WebSocket, specialist_id: str) -> None:
    from uuid import UUID

    resolved_id = UUID(specialist_id)
    await connection_manager.connect_specialist(resolved_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect_specialist(resolved_id, websocket)


@router.websocket("/queue/{patient_card_number}")
async def queue_socket(websocket: WebSocket, patient_card_number: str) -> None:
    await connection_manager.connect_queue(patient_card_number, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect_queue(patient_card_number, websocket)
