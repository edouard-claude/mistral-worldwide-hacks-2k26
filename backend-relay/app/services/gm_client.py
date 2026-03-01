import json
import logging
from collections.abc import Awaitable, Callable

import httpx

logger = logging.getLogger(__name__)

OnEvent = Callable[[dict], Awaitable[None]]


class GMClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0),
        )

    @property
    def is_ready(self) -> bool:
        return not self._client.is_closed

    async def start_game(self, lang: str = "fr") -> dict:
        resp = await self._client.get("/api/start", params={"lang": lang})
        resp.raise_for_status()
        return resp.json()

    async def get_state(self) -> dict:
        resp = await self._client.get("/api/state")
        resp.raise_for_status()
        return resp.json()

    async def get_wh26_status(self) -> dict:
        resp = await self._client.get("/api/wh26/status")
        resp.raise_for_status()
        return resp.json()

    async def stream_propose(self, lang: str, on_event: OnEvent) -> None:
        await self._consume_sse("/api/stream/propose", {"lang": lang}, on_event)

    async def stream_choose(self, kind: str, lang: str, on_event: OnEvent) -> None:
        await self._consume_sse(
            "/api/stream/choose", {"kind": kind, "lang": lang}, on_event
        )

    async def get_image(self, path: str) -> httpx.Response:
        resp = await self._client.get(f"/api/images/{path}")
        resp.raise_for_status()
        return resp

    async def _consume_sse(
        self, path: str, params: dict, on_event: OnEvent
    ) -> None:
        async with self._client.stream("GET", path, params=params) as resp:
            resp.raise_for_status()
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    raw_event, buffer = buffer.split("\n\n", 1)
                    await self._parse_sse_event(raw_event, on_event)

            # Handle any remaining data in buffer
            if buffer.strip():
                await self._parse_sse_event(buffer, on_event)

    async def _parse_sse_event(self, raw: str, on_event: OnEvent) -> None:
        data_lines: list[str] = []
        for line in raw.split("\n"):
            if line.startswith("data: "):
                data_lines.append(line[6:])
            elif line.startswith("data:"):
                data_lines.append(line[5:])

        if not data_lines:
            return

        data_str = "\n".join(data_lines)
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError:
            logger.warning("Non-JSON SSE data: %s", data_str[:200])
            return

        if isinstance(event, dict) and event.get("type") == "heartbeat":
            return

        await on_event(event)

    async def close(self) -> None:
        await self._client.aclose()
