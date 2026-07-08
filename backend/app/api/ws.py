import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.auth.jwt_handler import ACCESS_COOKIE, verify_token
from app.services.realtime import connection_manager


router = APIRouter(prefix="/ws", tags=["websocket"])


async def _ws_payload(websocket: WebSocket) -> dict | None:
    token = websocket.query_params.get("token") or websocket.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        return verify_token(token)
    except Exception:
        return None


@router.websocket("/triage")
async def triage_socket(websocket: WebSocket) -> None:
    payload = await _ws_payload(websocket)
    if payload is None or payload.get("type") not in {"STAFF", "SPECIALIST"}:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    resolved_tenant_id = UUID(tenant_id)
    await connection_manager.connect(resolved_tenant_id, websocket)
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            if data == "ping":
                await websocket.send_text("pong")
    except (asyncio.TimeoutError, WebSocketDisconnect):
        pass
    finally:
        connection_manager.disconnect(resolved_tenant_id, websocket)


@router.websocket("/specialist/{specialist_id}")
async def specialist_socket(websocket: WebSocket, specialist_id: str) -> None:
    payload = await _ws_payload(websocket)
    if payload is None or payload.get("type") not in {"SPECIALIST", "STAFF"}:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    resolved_id = UUID(specialist_id)
    await connection_manager.connect_specialist(resolved_id, websocket)
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            if data == "ping":
                await websocket.send_text("pong")
    except (asyncio.TimeoutError, WebSocketDisconnect):
        pass
    finally:
        connection_manager.disconnect_specialist(resolved_id, websocket)


@router.websocket("/queue/{patient_card_number}")
async def queue_socket(websocket: WebSocket, patient_card_number: str) -> None:
    await connection_manager.connect_queue(patient_card_number, websocket)
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            if data == "ping":
                await websocket.send_text("pong")
    except (asyncio.TimeoutError, WebSocketDisconnect):
        pass
    finally:
        connection_manager.disconnect_queue(patient_card_number, websocket)
