import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter()

_HEARTBEAT_INTERVAL = 30  # seconds — keep below proxy idle timeout (typically 60s)


@router.websocket("/ws/{session_id}")
async def websocket_arena(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    nats_relay = websocket.app.state.nats_relay
    session_manager = websocket.app.state.session_manager

    # Register in both systems
    await nats_relay.register_client(session_id, websocket)
    await session_manager.register_ws(session_id, websocket)

    async def _heartbeat() -> None:
        """Send periodic ping to keep the connection alive through proxies."""
        try:
            while websocket.client_state == WebSocketState.CONNECTED:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                try:
                    await websocket.send_json({"event": "heartbeat", "data": {}})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    heartbeat_task = asyncio.create_task(_heartbeat())

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    finally:
        heartbeat_task.cancel()
        await nats_relay.unregister_client(session_id, websocket)
        await session_manager.unregister_ws(session_id, websocket)
