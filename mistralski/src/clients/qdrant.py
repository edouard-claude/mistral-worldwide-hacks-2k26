"""Qdrant vector memory client for agent episodic memories."""

import uuid

import structlog
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.core.config import Settings
from src.core.exceptions import StorageError

logger = structlog.get_logger(__name__)


class MemoryPoint(BaseModel):
    """A memory entry with vector embedding."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str
    life_id: int
    tick: int
    text: str
    embedding: list[float]
    importance: float = 0.5
    metadata: dict[str, str] = Field(default_factory=dict)


class QdrantMemoryClient:
    """Client for storing and searching agent memories in Qdrant."""

    def __init__(self, settings: Settings) -> None:
        self._url = settings.qdrant_url
        self._collection = settings.qdrant_collection
        self._vector_size = settings.qdrant_vector_size
        self._client = AsyncQdrantClient(url=self._url)

    async def init_collection(self) -> None:
        """Create the memories collection if it doesn't exist."""
        collections = await self._client.get_collections()
        existing = [c.name for c in collections.collections]
        if self._collection not in existing:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_created", name=self._collection)

    async def store(self, memory: MemoryPoint) -> str:
        """Store a memory point.

        Args:
            memory: The memory entry to store.

        Returns:
            The memory ID.

        Raises:
            StorageError: On storage failure.
        """
        try:
            await self._client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=memory.id,
                        vector=memory.embedding,
                        payload={
                            "agent_id": memory.agent_id,
                            "life_id": memory.life_id,
                            "tick": memory.tick,
                            "text": memory.text,
                            "importance": memory.importance,
                            **memory.metadata,
                        },
                    )
                ],
            )
            return memory.id
        except Exception as e:
            raise StorageError(f"Qdrant upsert failed: {e}") from e

    async def search(
        self,
        embedding: list[float],
        agent_id: str,
        limit: int = 5,
        life_id: int | None = None,
    ) -> list[MemoryPoint]:
        """Search for similar memories.

        Args:
            embedding: Query vector.
            agent_id: Filter by agent.
            limit: Max results.
            life_id: Optional filter by specific life.

        Returns:
            List of matching MemoryPoints sorted by similarity.
        """
        must_filters = [{"key": "agent_id", "match": {"value": agent_id}}]
        if life_id is not None:
            must_filters.append({"key": "life_id", "match": {"value": life_id}})

        try:
            results = await self._client.query_points(
                collection_name=self._collection,
                query=embedding,
                query_filter={"must": must_filters},
                limit=limit,
                with_payload=True,
            )
            memories: list[MemoryPoint] = []
            for point in results.points:
                payload = point.payload or {}
                memories.append(
                    MemoryPoint(
                        id=str(point.id),
                        agent_id=payload.get("agent_id", agent_id),
                        life_id=payload.get("life_id", 0),
                        tick=payload.get("tick", 0),
                        text=payload.get("text", ""),
                        embedding=[],  # Don't return full vectors
                        importance=payload.get("importance", 0.5),
                    )
                )
            return memories
        except Exception as e:
            logger.error("qdrant_search_failed", error=str(e))
            return []

    async def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Qdrant client."""
        await self._client.close()
