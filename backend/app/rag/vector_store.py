"""Vector store abstraction with Qdrant implementation for the RAG pipeline."""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Point:
    """A vector point to store or retrieve."""

    id: str
    vector: List[float]
    payload: Dict[str, Any]


@dataclass
class ScoredPoint:
    """A scored search result."""

    id: str
    score: float
    payload: Dict[str, Any]


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def add(self, collection: str, points: List[Point]) -> None:
        """Add points to a collection."""

    @abstractmethod
    async def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Dict[str, Any] | None = None,
    ) -> List[ScoredPoint]:
        """Search a collection by vector similarity."""

    @abstractmethod
    async def delete(self, collection: str, point_ids: List[str]) -> None:
        """Delete points from a collection."""

    @abstractmethod
    async def rebuild(self, collection: str, vector_size: int = 1024) -> None:
        """Recreate a collection (destructive)."""


class QdrantStore(VectorStore):
    """Qdrant-backed vector store using AsyncQdrantClient."""

    def __init__(self, client: AsyncQdrantClient | None = None) -> None:
        self._client = client
        self._settings = get_settings()
        self._vector_size: int = 1024

    def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(
                host=self._settings.QDRANT_HOST,
                port=self._settings.QDRANT_PORT,
            )
        return self._client

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    async def _ensure_collection(self, collection: str, vector_size: int = 1024) -> None:
        client = self._get_client()
        try:
            collections = await client.get_collections()
            existing = {c.name for c in collections.collections}
            if collection not in existing:
                logger.info("Creating Qdrant collection: %s", collection)
                await client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE,
                    ),
                )
        except Exception as exc:
            logger.error("Failed to ensure collection %s: %s", collection, exc)
            raise

    # ------------------------------------------------------------------
    # VectorStore interface
    # ------------------------------------------------------------------

    async def add(self, collection: str, points: List[Point]) -> None:
        if not points:
            return

        # Infer vector size from first point
        vector_size = len(points[0].vector)
        await self._ensure_collection(collection, vector_size)

        client = self._get_client()
        point_structs = []
        for p in points:
            qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, p.id))
            payload = dict(p.payload)
            payload["_point_id"] = p.id
            point_structs.append(
                PointStruct(
                    id=qdrant_id,
                    vector=p.vector,
                    payload=payload,
                )
            )

        try:
            await client.upsert(collection_name=collection, points=point_structs)
            logger.debug("Upserted %d points into %s", len(points), collection)
        except Exception as exc:
            logger.error("Failed to upsert points into %s: %s", collection, exc)
            raise

    async def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 10,
        filters: Dict[str, Any] | None = None,
    ) -> List[ScoredPoint]:
        client = self._get_client()

        qdrant_filter = self._build_filter(filters) if filters else None

        try:
            from qdrant_client.http.models import Filter as QdrantFilter
            search_filter = qdrant_filter if qdrant_filter else None
            results = await client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=top_k,
                query_filter=search_filter,
                with_payload=True,
            )
            results = results.points
        except Exception as exc:
            logger.error("Search failed in collection %s: %s", collection, exc)
            raise

        return [
            ScoredPoint(
                id=str(r.id),
                score=r.score,
                payload=dict(r.payload) if r.payload else {},
            )
            for r in results
        ]

    async def delete(self, collection: str, point_ids: List[str]) -> None:
        if not point_ids:
            return

        client = self._get_client()
        try:
            await client.delete(
                collection_name=collection,
                points_selector=point_ids,
            )
            logger.debug("Deleted %d points from %s", len(point_ids), collection)
        except Exception as exc:
            logger.error("Failed to delete points from %s: %s", collection, exc)
            raise

    async def rebuild(self, collection: str, vector_size: int | None = None) -> None:
        client = self._get_client()
        try:
            collections = await client.get_collections()
            existing = {c.name for c in collections.collections}
            if collection in existing:
                logger.info("Deleting existing collection: %s", collection)
                await client.delete_collection(collection_name=collection)
            else:
                logger.info("Collection %s does not exist, nothing to delete", collection)
            logger.info("Collection %s deleted (will be recreated on first add)", collection)
        except Exception as exc:
            logger.error("Failed to rebuild collection %s: %s", collection, exc)
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filter(filters: Dict[str, Any]) -> Filter | None:
        """Build a Qdrant Filter from a simple dict of payload matches."""
        conditions: List[FieldCondition] = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )
        if not conditions:
            return None
        return Filter(must=conditions)


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_vector_store: QdrantStore | None = None


def get_vector_store() -> QdrantStore:
    """Return a singleton QdrantStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = QdrantStore()
    return _vector_store
