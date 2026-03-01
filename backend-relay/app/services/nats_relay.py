import json
import logging
import random
from pathlib import Path

from fastapi import WebSocket
from nats.aio.client import Client as NatsClient
from nats.aio.msg import Msg

logger = logging.getLogger(__name__)

_SKINS_DIR = Path(__file__).resolve().parent.parent.parent / "public" / "agent-skins"
_AVAILABLE_SKINS = [p.stem for p in _SKINS_DIR.glob("*.png")]


def _avatar_url(agent_name: str) -> str:
    name = agent_name.lower()
    if name not in _AVAILABLE_SKINS:
        name = random.choice(_AVAILABLE_SKINS)
    return f"/static/agent-skins/{name}.png"


def _enrich_payload(payload: dict | list | str) -> dict | list | str:
    """Inject avatar_url fields into payloads containing agent names."""
    if isinstance(payload, list):
        return [_enrich_payload(item) for item in payload]
    if not isinstance(payload, dict):
        return payload

    # Direct agent_name field (AgentMessage, DeathEvent)
    if "agent_name" in payload:
        payload["avatar_url"] = _avatar_url(payload["agent_name"])

    # CloneEvent: parent_name / child_name
    for key in ("parent_name", "child_name"):
        if key in payload:
            payload[key.replace("name", "avatar_url")] = _avatar_url(payload[key])

    # GlobalState: agents array and graveyard
    for list_key in ("agents", "graveyard"):
        if list_key in payload and isinstance(payload[list_key], list):
            for agent in payload[list_key]:
                if isinstance(agent, dict) and "name" in agent:
                    agent["avatar_url"] = _avatar_url(agent["name"])

    # EndEvent: survivors list → convert to objects with avatar
    if "survivors" in payload and isinstance(payload["survivors"], list):
        enriched = []
        for name in payload["survivors"]:
            if isinstance(name, str):
                enriched.append({"name": name, "avatar_url": _avatar_url(name)})
            else:
                enriched.append(name)
        payload["survivors"] = enriched

    return payload


class NatsRelay:
    def __init__(self, nats_url: str) -> None:
        self._nats_url = nats_url
        self._nc: NatsClient = NatsClient()
        self._sessions: dict[str, set[WebSocket]] = {}

    @property
    def is_connected(self) -> bool:
        return self._nc.is_connected

    async def connect(self) -> None:
        await self._nc.connect(
            self._nats_url,
            reconnected_cb=self._on_reconnect,
            disconnected_cb=self._on_disconnect,
            error_cb=self._on_error,
        )
        logger.info("NATS connected to %s", self._nats_url)

        await self._nc.subscribe("arena.>", cb=self._message_handler)
        logger.info("Subscribed to arena.>")

    async def _message_handler(self, msg: Msg) -> None:
        parts = msg.subject.split(".")
        if len(parts) < 3:
            logger.warning("Unexpected NATS subject format: %s", msg.subject)
            return

        session_id = parts[1]
        topic_suffix = ".".join(parts[2:])

        # Skip messages the backend itself published (self-echo prevention)
        if topic_suffix.startswith("input.fakenews"):
            return

        clients = self._sessions.get(session_id)
        if not clients:
            return

        # Decode payload
        try:
            payload = json.loads(msg.data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = msg.data.decode()

        payload = _enrich_payload(payload)
        envelope = {"event": f"arena.{topic_suffix}", "data": payload}

        # Send to all connected clients for this session
        dead_clients: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_json(envelope)
            except Exception:
                dead_clients.append(ws)
                logger.warning("Failed to send to WebSocket client in session %s, removing", session_id)

        for ws in dead_clients:
            clients.discard(ws)
        if not clients:
            self._sessions.pop(session_id, None)

    async def register_client(self, session_id: str, ws: WebSocket) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = set()
        self._sessions[session_id].add(ws)
        logger.info("Client registered for session %s", session_id)

    async def unregister_client(self, session_id: str, ws: WebSocket) -> None:
        clients = self._sessions.get(session_id)
        if clients:
            clients.discard(ws)
            if not clients:
                self._sessions.pop(session_id, None)
        logger.info("Client unregistered from session %s", session_id)

    async def publish_init(self, session_id: str, query_params: dict | None = None) -> None:
        if not self._nc.is_connected:
            raise RuntimeError("NATS is not connected")
        topic = "arena.init"
        payload_dict: dict = {"session_id": session_id}
        if query_params:
            payload_dict["query_params"] = query_params
        payload = json.dumps(payload_dict).encode("utf-8")
        await self._nc.publish(topic, payload)
        logger.info("Published init to %s for session %s", topic, session_id)

    async def publish_fakenews(self, session_id: str, content: str, query_params: dict | None = None) -> None:
        if not self._nc.is_connected:
            raise RuntimeError("NATS is not connected")
        topic = f"arena.{session_id}.input.fakenews"
        payload_dict: dict = {"content": content}
        if query_params:
            payload_dict["query_params"] = query_params
        payload = json.dumps(payload_dict).encode("utf-8")
        await self._nc.publish(topic, payload)
        logger.info("Published fakenews to %s", topic)

    async def disconnect(self) -> None:
        try:
            if self._nc.is_connected:
                await self._nc.drain()
                logger.info("NATS connection drained and closed")
        except Exception:
            logger.exception("Error during NATS disconnect")

    async def _on_reconnect(self) -> None:
        logger.info("NATS reconnected to %s", self._nc.connected_url)

    async def _on_disconnect(self) -> None:
        logger.warning("NATS disconnected")

    async def _on_error(self, e: Exception) -> None:
        logger.error("NATS error: %s", e)
