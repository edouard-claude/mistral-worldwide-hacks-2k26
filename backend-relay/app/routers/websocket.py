import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_arena(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    nats_relay = websocket.app.state.nats_relay
    session_manager = websocket.app.state.session_manager

    # Register in both systems
    await nats_relay.register_client(session_id, websocket)
    await session_manager.register_ws(session_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await nats_relay.unregister_client(session_id, websocket)
        await session_manager.unregister_ws(session_id, websocket)
        logger.info("WebSocket disconnected for session %s", session_id)
