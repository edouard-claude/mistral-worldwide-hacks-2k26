"""vLLM batch inference client with concurrent request support."""

import asyncio
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

from src.core.config import Settings
from src.core.exceptions import LLMError

logger = structlog.get_logger(__name__)


class InferenceRequest(BaseModel):
    """A single inference request for batch processing."""

    prompt: str
    system: str = ""
    model: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7
    json_mode: bool = False


class VLLMBatchClient:
    """Client for vLLM server supporting batch inference via concurrent requests.

    vLLM handles continuous batching server-side, so N concurrent HTTP requests
    are efficiently batched into a single GPU pass.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.vllm_base_url.rstrip("/")
        self._api_key = settings.vllm_api_key.get_secret_value()
        self._default_model = settings.vllm_agent_model
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
        )

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        """Generate a single completion.

        Args:
            prompt: User message content.
            system: System prompt.
            model: Model ID (defaults to agent model).
            max_tokens: Max tokens to generate.
            temperature: Sampling temperature.
            json_mode: Force JSON output format.

        Returns:
            Generated text content.

        Raises:
            LLMError: On request failure.
        """
        model = model or self._default_model
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = await self._client.post("/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                logger.warning("vllm_overloaded, retrying once")
                await asyncio.sleep(1.0)
                resp = await self._client.post("/v1/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            raise LLMError(f"vLLM request failed: {e}") from e
        except httpx.HTTPError as e:
            raise LLMError(f"vLLM connection error: {e}") from e

    async def batch_generate(self, requests: list[InferenceRequest]) -> list[str]:
        """Send N inference requests concurrently (vLLM batches server-side).

        Args:
            requests: List of inference requests.

        Returns:
            List of generated texts in same order as requests.
        """
        tasks = [
            self.generate(
                prompt=req.prompt,
                system=req.system,
                model=req.model,
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                json_mode=req.json_mode,
            )
            for req in requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("batch_request_failed", index=i, error=str(result))
                outputs.append("")
            else:
                outputs.append(result)
        return outputs

    async def health_check(self) -> bool:
        """Check if vLLM server is reachable."""
        try:
            resp = await self._client.get("/v1/models")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
