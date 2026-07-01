"""Embedding service with multi-provider support for the RAG pipeline."""

import asyncio
import logging
from typing import List, Literal

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Local embedding model (fastembed - lightweight, no PyTorch needed)
_local_model = None
_LOCAL_MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def _get_local_model():
    """Lazy-load the local embedding model via fastembed."""
    global _local_model
    if _local_model is not None:
        return _local_model

    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise ImportError(
            "fastembed is not installed. Install it: pip install fastembed"
        ) from exc

    logger.info("Loading local embedding model: %s", _LOCAL_MODEL_NAME)
    _local_model = TextEmbedding(model_name=_LOCAL_MODEL_NAME)
    return _local_model


class EmbeddingService:
    """Unified async embedding service with provider fallback."""

    def __init__(
        self,
        provider: Literal["deepseek", "local"] = "local",
        model_name: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 32,
    ) -> None:
        self.provider = provider
        self.dimensions = dimensions
        self.batch_size = batch_size

        if provider == "deepseek":
            self.model_name = model_name or ""
        elif provider == "local":
            self.model_name = model_name or _LOCAL_MODEL_NAME
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self._settings = get_settings()
        self._http_client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts in batches."""
        if not texts:
            return []

        # Filter out empty strings
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return [[] for _ in texts]

        all_embeddings: List[List[float]] = []
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i : i + self.batch_size]
            try:
                batch_embeddings = await self._embed_batch(batch)
            except Exception as exc:
                logger.error("Embedding batch failed: %s", exc)
                if self.provider == "deepseek":
                    logger.warning("Falling back to local embeddings")
                    batch_embeddings = await self._embed_batch_local(batch)
                else:
                    raise
            # Auto-detect dimensions from first embedding result
            if self.dimensions is None and batch_embeddings:
                self.dimensions = len(batch_embeddings[0])
            all_embeddings.extend(batch_embeddings)

        # Map back to original order (including empty strings)
        result: List[List[float]] = []
        emb_iter = iter(all_embeddings)
        for t in texts:
            if t and t.strip():
                result.append(next(emb_iter))
            else:
                result.append([0.0] * self.dimensions)
        return result

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        embeddings = await self.embed([text])
        return embeddings[0] if embeddings else [0.0] * self.dimensions

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.provider == "deepseek":
            return await self._embed_batch_deepseek(texts)
        if self.provider == "local":
            return await self._embed_batch_local(texts)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _embed_batch_deepseek(self, texts: List[str]) -> List[List[float]]:
        api_key = self._settings.LLM_API_KEY.get_secret_value()
        base_url = self._settings.LLM_BASE_URL.rstrip("/")
        client = self._get_client()

        response = await client.post(
            f"{base_url}/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "input": texts,
                "encoding_format": "float",
            },
        )
        response.raise_for_status()
        data = response.json()

        embeddings = [item["embedding"] for item in data["data"]]
        # Ensure consistent dimensions
        normalized = [_normalize_vector(v, self.dimensions) for v in embeddings]
        return normalized

    async def _embed_batch_local(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_event_loop()
        model = _get_local_model()
        embeddings = await loop.run_in_executor(
            None, lambda: list(model.embed(texts))
        )
        embeddings_list = [e.tolist() for e in embeddings]
        # Auto-detect dimensions from first result
        if self.dimensions is None and embeddings_list:
            self.dimensions = len(embeddings_list[0])
        dim = self.dimensions or len(embeddings_list[0]) if embeddings_list else 512
        normalized = [_normalize_vector(v, dim) for v in embeddings_list]
        return normalized


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_embedding_service: EmbeddingService | None = None


def get_embedding_service(
    provider: Literal["deepseek", "local"] = "local",
    model_name: str | None = None,
    dimensions: int | None = None,
    batch_size: int = 32,
) -> EmbeddingService:
    """Return a singleton EmbeddingService instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(
            provider=provider,
            model_name=model_name,
            dimensions=dimensions,
            batch_size=batch_size,
        )
    return _embedding_service


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _normalize_vector(vector: List[float], target_dim: int) -> List[float]:
    """Normalize vector length to target_dim by padding or truncating."""
    if len(vector) == target_dim:
        return vector
    if len(vector) > target_dim:
        return vector[:target_dim]
    # Pad with zeros
    return vector + [0.0] * (target_dim - len(vector))
