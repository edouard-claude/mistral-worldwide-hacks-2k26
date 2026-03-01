import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.messages import InitSessionInput, SubmitNewsInput

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/init_session")
async def init_session(body: InitSessionInput, request: Request) -> JSONResponse:
    session_manager = request.app.state.session_manager
    nats_relay = request.app.state.nats_relay

    try:
        await session_manager.create_session(body.session_id)
    except FileExistsError:
        return JSONResponse(
            status_code=400,
            content={"error": "Session already exists"},
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )

    if not nats_relay.is_connected:
        return JSONResponse(
            status_code=503,
            content={"error": "NATS is not connected"},
        )

    await nats_relay.publish_init(body.session_id)

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "session_id": body.session_id},
    )


@router.post("/submit_news")
async def submit_news(body: SubmitNewsInput, request: Request) -> JSONResponse:
    session_manager = request.app.state.session_manager

    if not session_manager.session_exists(body.session_id):
        return JSONResponse(
            status_code=404,
            content={"error": "Session not found"},
        )

    nats_relay = request.app.state.nats_relay
    if not nats_relay.is_connected:
        return JSONResponse(
            status_code=503,
            content={"error": "NATS is not connected"},
        )

    await nats_relay.publish_fakenews(body.session_id, body.content)

    return JSONResponse(
        status_code=200,
        content={"status": "published", "session_id": body.session_id},
    )
