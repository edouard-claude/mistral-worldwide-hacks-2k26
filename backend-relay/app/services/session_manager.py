import asyncio
import json
import logging
from dataclasses import dataclass, field

from fastapi import WebSocket

from app.schemas.messages import SESSION_ID_PATTERN

logger = logging.getLogger(__name__)


@dataclass
class Session:
    session_id: str
    gm_session_id: str | None = None
    lang: str = "fr"
    ws_clients: set[WebSocket] = field(default_factory=set)
    active_task: asyncio.Task | None = None  # type: ignore[type-arg]
    game_data: dict = field(default_factory=dict)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def create_session(self, session_id: str, lang: str = "fr") -> Session:
        if not SESSION_ID_PATTERN.match(session_id):
            raise ValueError("Invalid session_id format")

        if session_id in self._sessions:
            raise FileExistsError(f"Session {session_id} already exists")

        session = Session(session_id=session_id, lang=lang)
        self._sessions[session_id] = session
        return session

    def get_or_create_session_sync(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            if not SESSION_ID_PATTERN.match(session_id):
                raise ValueError("Invalid session_id format")
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    async def register_ws(self, session_id: str, ws: WebSocket) -> None:
        session = self.get_or_create_session_sync(session_id)
        session.ws_clients.add(ws)
        logger.info(
            "WS registered for session %s (total: %d)",
            session_id,
            len(session.ws_clients),
        )

    async def unregister_ws(self, session_id: str, ws: WebSocket) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.ws_clients.discard(ws)
            logger.info(
                "WS unregistered from session %s (remaining: %d)",
                session_id,
                len(session.ws_clients),
            )

    async def broadcast(self, session_id: str, event: str, data: dict | list | str) -> None:
        session = self._sessions.get(session_id)
        if not session or not session.ws_clients:
            return

        envelope = json.dumps({"event": event, "data": data})
        dead: list[WebSocket] = []

        for ws in session.ws_clients:
            try:
                await ws.send_text(envelope)
            except Exception:
                dead.append(ws)
                logger.warning("Failed to send to WS in session %s, removing", session_id)

        for ws in dead:
            session.ws_clients.discard(ws)

    def cancel_active_task(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session and session.active_task and not session.active_task.done():
            session.active_task.cancel()
            logger.info("Cancelled active task for session %s", session_id)

    def set_active_task(self, session_id: str, task: asyncio.Task) -> None:  # type: ignore[type-arg]
        session = self._sessions.get(session_id)
        if session:
            session.active_task = task
