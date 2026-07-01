"""Semantic caching service using Redis and embedding similarity."""

import hashlib
import json
import logging
import math
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SemanticCache:
    """Caches agent pipeline results keyed by query embedding similarity."""

    def __init__(
        self,
        redis_client,
        embedding_service,
        threshold: float = 0.92,
        ttl: int = 3600,
    ) -> None:
        self.redis = redis_client
        self.embedding_service = embedding_service
        self.threshold = threshold
        self.ttl = ttl
        self._embedding_key = "cache:embeddings"

    async def get(self, query: str, user_id: str) -> Optional[dict]:
        """Lookup a cached result for a semantically similar query."""
        try:
            query_embedding = await self.embedding_service.embed_query(query)
        except Exception:
            logger.exception("Embedding failed for cache lookup, skipping cache")
            return None

        if not query_embedding or all(v == 0.0 for v in query_embedding):
            return None

        try:
            entries = await self.redis.zrevrange(
                self._embedding_key, 0, 99, withscores=True
            )
        except Exception:
            logger.exception("Redis lookup failed for cache get")
            return None

        for entry_key_raw, _timestamp in entries:
            entry_key = (
                entry_key_raw.decode("utf-8")
                if isinstance(entry_key_raw, bytes)
                else entry_key_raw
            )
            try:
                data_raw = await self.redis.get(entry_key)
                if not data_raw:
                    continue
                data = json.loads(data_raw)
                cached_embedding = data.get("embedding")
                if not cached_embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                if similarity >= self.threshold:
                    logger.info(
                        "Cache HIT for user=%s query=%s (sim=%.3f)",
                        user_id,
                        query[:50],
                        similarity,
                    )
                    return {
                        "query": data["query"],
                        "result": data["result"],
                        "similarity": similarity,
                        "timestamp": data.get("timestamp"),
                    }
            except Exception:
                logger.exception("Error comparing cache entry %s", entry_key)
                continue

        logger.debug("Cache MISS for user=%s query=%s", user_id, query[:50])
        return None

    async def set(self, query: str, user_id: str, result: Any) -> None:
        """Store a result in the semantic cache."""
        try:
            query_embedding = await self.embedding_service.embed_query(query)
        except Exception:
            logger.exception("Embedding failed for cache set, skipping cache")
            return

        if not query_embedding or all(v == 0.0 for v in query_embedding):
            return

        try:
            timestamp = time.time()
            query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
            cache_key = f"cache:{query_hash}:{user_id}"

            payload = {
                "query": query,
                "result": result,
                "embedding": query_embedding,
                "timestamp": timestamp,
            }

            pipe = self.redis.pipeline()
            pipe.set(cache_key, json.dumps(payload), ex=self.ttl)
            pipe.zadd(self._embedding_key, {cache_key: timestamp})
            pipe.zremrangebyrank(self._embedding_key, 0, -1001)
            await pipe.execute()

            logger.info(
                "Cache SET for user=%s query=%s key=%s",
                user_id,
                query[:50],
                cache_key,
            )
        except Exception:
            logger.exception("Redis write failed for cache set")

    async def invalidate(self, pattern: str = "*") -> int:
        """Remove cached entries. pattern='*' clears all; otherwise matches user_id."""
        try:
            if pattern == "*":
                keys = await self.redis.zrange(self._embedding_key, 0, -1)
                if keys:
                    pipe = self.redis.pipeline()
                    for key in keys:
                        pipe.delete(key)
                    pipe.delete(self._embedding_key)
                    await pipe.execute()
                return len(keys) if keys else 0
            else:
                matched = []
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(
                        cursor, match=f"cache:*:{pattern}"
                    )
                    if keys:
                        matched.extend(keys)
                    if cursor == 0:
                        break

                if matched:
                    pipe = self.redis.pipeline()
                    for key in matched:
                        pipe.delete(key)
                        pipe.zrem(self._embedding_key, key)
                    await pipe.execute()
                return len(matched)
        except Exception:
            logger.exception("Cache invalidation failed")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        try:
            total_entries = await self.redis.zcard(self._embedding_key)
            keys = await self.redis.zrange(self._embedding_key, 0, 9)
            total_size = 0
            for key in keys:
                size = await self.redis.memory_usage(key)
                if size:
                    total_size += size
            avg_size = total_size / len(keys) if keys else 0
            estimated_memory = int(avg_size * total_entries)

            return {
                "total_entries": total_entries,
                "threshold": self.threshold,
                "ttl": self.ttl,
                "estimated_memory_bytes": estimated_memory,
            }
        except Exception:
            logger.exception("Cache stats retrieval failed")
            return {
                "total_entries": 0,
                "threshold": self.threshold,
                "ttl": self.ttl,
                "estimated_memory_bytes": 0,
            }

    @staticmethod
    def _cosine_similarity(a: list, b: list) -> float:
        """Compute cosine similarity between two vectors using math.sqrt."""
        if len(a) != len(b):
            min_len = min(len(a), len(b))
            a = a[:min_len]
            b = b[:min_len]

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / (norm_a * norm_b)
