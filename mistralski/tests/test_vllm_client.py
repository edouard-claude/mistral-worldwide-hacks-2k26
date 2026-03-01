"""Tests for vLLM batch client."""

import pytest
import respx
from httpx import Response

from src.clients.vllm import InferenceRequest, VLLMBatchClient
from src.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        vllm_base_url="http://test-vllm:8000",
        vllm_api_key="test-key",
    )


@pytest.fixture
def client(settings: Settings) -> VLLMBatchClient:
    return VLLMBatchClient(settings)


def _chat_response(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": 10},
    }


@respx.mock
@pytest.mark.asyncio
async def test_generate_success(client: VLLMBatchClient) -> None:
    respx.post("http://test-vllm:8000/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response("Hello world"))
    )
    result = await client.generate("Say hello")
    assert result == "Hello world"


@respx.mock
@pytest.mark.asyncio
async def test_generate_json_mode(client: VLLMBatchClient) -> None:
    route = respx.post("http://test-vllm:8000/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response('{"action": "move"}'))
    )
    result = await client.generate("Decide action", json_mode=True)
    assert '"action"' in result
    request_body = route.calls[0].request.content
    assert b"json_object" in request_body


@respx.mock
@pytest.mark.asyncio
async def test_batch_generate(client: VLLMBatchClient) -> None:
    respx.post("http://test-vllm:8000/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response("batch result"))
    )
    requests = [InferenceRequest(prompt=f"Prompt {i}") for i in range(3)]
    results = await client.batch_generate(requests)
    assert len(results) == 3
    assert all(r == "batch result" for r in results)


@respx.mock
@pytest.mark.asyncio
async def test_generate_retry_on_503(client: VLLMBatchClient) -> None:
    respx.post("http://test-vllm:8000/v1/chat/completions").mock(
        side_effect=[
            Response(503, text="overloaded"),
            Response(200, json=_chat_response("recovered")),
        ]
    )
    result = await client.generate("test retry")
    assert result == "recovered"


@respx.mock
@pytest.mark.asyncio
async def test_health_check(client: VLLMBatchClient) -> None:
    respx.get("http://test-vllm:8000/v1/models").mock(return_value=Response(200, json={"data": []}))
    assert await client.health_check() is True


@respx.mock
@pytest.mark.asyncio
async def test_health_check_failure(client: VLLMBatchClient) -> None:
    respx.get("http://test-vllm:8000/v1/models").mock(return_value=Response(500, text="error"))
    assert await client.health_check() is False
