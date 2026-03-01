import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers.arena import router as arena_router
from app.routers.websocket import router as ws_router
from app.services.nats_relay import NatsRelay
from app.services.session_manager import SessionManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.session_manager = SessionManager()
    logger.info("SessionManager initialized (in-memory)")

    nats_url = os.getenv("NATS_URL", "nats://demo.nats.io:4222")
    nats_relay = NatsRelay(nats_url)
    try:
        await nats_relay.connect()
    except Exception:
        logger.exception("Failed to connect to NATS at %s — app running without NATS", nats_url)
    app.state.nats_relay = nats_relay

    yield

    await app.state.nats_relay.disconnect()


app = FastAPI(title="bmadlife-backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(arena_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    if errors:
        first = errors[0]
        msg = first.get("msg", "Validation error")
    else:
        msg = "Validation error"
    return JSONResponse(status_code=400, content={"error": msg})


@app.get("/health")
async def health(request: Request) -> dict:
    nats_relay = getattr(request.app.state, "nats_relay", None)
    nats_connected = nats_relay.is_connected if nats_relay else False
    return {
        "status": "ok",
        "service": "bmadlife-backend",
        "nats_connected": nats_connected,
    }
