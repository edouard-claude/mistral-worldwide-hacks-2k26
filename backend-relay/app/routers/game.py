import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.services.gm_client import GMClient
from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _get_gm(request: Request) -> GMClient:
    return request.app.state.gm_client


def _get_sm(request: Request) -> SessionManager:
    return request.app.state.session_manager


@router.get("/start")
async def start_game(request: Request, lang: str = "fr") -> JSONResponse:
    gm = _get_gm(request)
    sm = _get_sm(request)
    nats_relay = request.app.state.nats_relay

    try:
        result = await gm.start_game(lang)
    except Exception:
        logger.exception("Failed to call GM /api/start")
        return JSONResponse(status_code=502, content={"error": "GM unreachable"})

    # Extract session_id from GM response and create relay session
    gm_session_id = result.get("session_id")
    if gm_session_id:
        try:
            session = await sm.create_session(gm_session_id, lang=lang)
            session.gm_session_id = gm_session_id
        except FileExistsError:
            pass  # Session already exists, that's fine

        # Publish init to NATS so swarm starts listening for this session
        if nats_relay.is_connected:
            try:
                await nats_relay.publish_init(gm_session_id, {"lang": lang})
                logger.info("Published arena.init for session %s", gm_session_id)
            except Exception:
                logger.exception("Failed to publish arena.init for session %s", gm_session_id)

    return JSONResponse(content=result)


@router.get("/state")
async def get_state(request: Request) -> JSONResponse:
    gm = _get_gm(request)
    try:
        result = await gm.get_state()
    except Exception:
        logger.exception("Failed to call GM /api/state")
        return JSONResponse(status_code=502, content={"error": "GM unreachable"})
    return JSONResponse(content=result)


@router.get("/propose")
async def propose(request: Request, session_id: str, lang: str = "fr") -> JSONResponse:
    gm = _get_gm(request)
    sm = _get_sm(request)

    if not sm.session_exists(session_id):
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    # Cancel any running task for this session
    sm.cancel_active_task(session_id)

    async def _stream_propose() -> None:
        try:
            async def on_event(event: dict) -> None:
                event_type = event.get("type", "unknown")
                await sm.broadcast(session_id, f"gm.{event_type}", event)

            await gm.stream_propose(lang, on_event)
        except asyncio.CancelledError:
            logger.info("Propose task cancelled for session %s", session_id)
        except Exception:
            logger.exception("Error in propose stream for session %s", session_id)
            await sm.broadcast(session_id, "gm.error", {"error": "Propose stream failed"})

    task = asyncio.create_task(_stream_propose())
    sm.set_active_task(session_id, task)

    return JSONResponse(status_code=202, content={"status": "streaming", "session_id": session_id})


@router.get("/choose")
async def choose(request: Request, session_id: str, kind: str, lang: str = "fr") -> JSONResponse:
    gm = _get_gm(request)
    sm = _get_sm(request)

    if not sm.session_exists(session_id):
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    # Cancel any running task for this session
    sm.cancel_active_task(session_id)

    async def _stream_choose() -> None:
        try:
            async def on_event(event: dict) -> None:
                event_type = event.get("type", "unknown")
                await sm.broadcast(session_id, f"gm.{event_type}", event)

            await gm.stream_choose(kind, lang, on_event)
        except asyncio.CancelledError:
            logger.info("Choose task cancelled for session %s", session_id)
        except Exception:
            logger.exception("Error in choose stream for session %s", session_id)
            await sm.broadcast(session_id, "gm.error", {"error": "Choose stream failed"})

    task = asyncio.create_task(_stream_choose())
    sm.set_active_task(session_id, task)

    return JSONResponse(status_code=202, content={"status": "streaming", "session_id": session_id})


@router.get("/images/{gm_session_id}/{filename:path}")
async def proxy_image(request: Request, gm_session_id: str, filename: str) -> Response:
    gm = _get_gm(request)
    try:
        resp = await gm.get_image(f"{gm_session_id}/{filename}")
        content_type = resp.headers.get("content-type", "image/png")
        return Response(content=resp.content, media_type=content_type)
    except Exception:
        logger.exception("Failed to proxy image %s/%s", gm_session_id, filename)
        return JSONResponse(status_code=502, content={"error": "Image fetch failed"})
