"""Tests for Qdrant memory client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.clients.qdrant import MemoryPoint, QdrantMemoryClient
from src.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        qdrant_url="http://test-qdrant:6333",
        qdrant_collection="test_memories",
        qdrant_vector_size=128,
    )


@pytest.fixture
def mock_qdrant_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(settings: Settings, mock_qdrant_client: AsyncMock) -> QdrantMemoryClient:
    qc = QdrantMemoryClient(settings)
    qc._client = mock_qdrant_client
    return qc


@pytest.mark.asyncio
async def test_init_collection_creates_if_missing(
    client: QdrantMemoryClient, mock_qdrant_client: AsyncMock
) -> None:
    collections_response = MagicMock()
    collections_response.collections = []
    mock_qdrant_client.get_collections.return_value = collections_response

    await client.init_collection()

    mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_init_collection_skips_if_exists(
    client: QdrantMemoryClient, mock_qdrant_client: AsyncMock
) -> None:
    collection = MagicMock()
    collection.name = "test_memories"
    collections_response = MagicMock()
    collections_response.collections = [collection]
    mock_qdrant_client.get_collections.return_value = collections_response

    await client.init_collection()

    mock_qdrant_client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_store_memory(client: QdrantMemoryClient, mock_qdrant_client: AsyncMock) -> None:
    memory = MemoryPoint(
        agent_id="agent_01",
        life_id=1,
        tick=42,
        text="Found food at bakery",
        embedding=[0.1] * 128,
        importance=0.8,
    )
    mock_qdrant_client.upsert.return_value = None

    result = await client.store(memory)
    assert result == memory.id
    mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_search_memories(client: QdrantMemoryClient, mock_qdrant_client: AsyncMock) -> None:
    point = MagicMock()
    point.id = "test-id"
    point.payload = {
        "agent_id": "agent_01",
        "life_id": 1,
        "tick": 42,
        "text": "Found food",
        "importance": 0.8,
    }
    results_response = MagicMock()
    results_response.points = [point]
    mock_qdrant_client.query_points.return_value = results_response

    results = await client.search(
        embedding=[0.1] * 128,
        agent_id="agent_01",
        limit=5,
    )
    assert len(results) == 1
    assert results[0].text == "Found food"
    assert results[0].agent_id == "agent_01"


@pytest.mark.asyncio
async def test_health_check(client: QdrantMemoryClient, mock_qdrant_client: AsyncMock) -> None:
    mock_qdrant_client.get_collections.return_value = MagicMock()
    assert await client.health_check() is True


@pytest.mark.asyncio
async def test_health_check_failure(
    client: QdrantMemoryClient, mock_qdrant_client: AsyncMock
) -> None:
    mock_qdrant_client.get_collections.side_effect = Exception("connection refused")
    assert await client.health_check() is False
