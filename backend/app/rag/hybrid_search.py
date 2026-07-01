"""Hybrid search combining BM25 (Whoosh) and dense vector search with RRF fusion."""

import asyncio
import logging
import tempfile
from typing import Any, Dict, List, Tuple

from whoosh import index
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import ID, TEXT, Schema
from whoosh.qparser import QueryParser
from whoosh.searching import Searcher

from app.rag.vector_store import QdrantStore, ScoredPoint, get_vector_store

logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid search combining BM25 keyword search and dense vector search."""

    def __init__(
        self,
        vector_store: QdrantStore | None = None,
        alpha: float = 0.3,
        rrf_k: int = 60,
    ) -> None:
        self.vector_store = vector_store or get_vector_store()
        self.alpha = alpha
        self.rrf_k = rrf_k

        # In-memory Whoosh index
        self._index: index.Index | None = None
        self._searcher: Searcher | None = None
        self._doc_map: Dict[str, Dict[str, Any]] = {}
        self._temp_dir: str | None = None

    # ------------------------------------------------------------------
    # BM25 index management
    # ------------------------------------------------------------------

    def build_bm25_index(
        self,
        documents: List[str],
        payloads: List[Dict[str, Any]] | None = None,
    ) -> None:
        """Build an in-memory Whoosh BM25 index from documents."""
        if not documents:
            logger.warning("No documents provided for BM25 index")
            return

        schema = Schema(
            doc_id=ID(stored=True, unique=True),
            content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        )

        # Create a temporary in-memory directory for the index
        self._temp_dir = tempfile.mkdtemp(prefix="whoosh_")
        self._index = index.create_in(self._temp_dir, schema)

        writer = self._index.writer()
        self._doc_map = {}

        for idx, text in enumerate(documents):
            doc_id = f"doc_{idx}"
            writer.add_document(doc_id=doc_id, content=text)
            self._doc_map[doc_id] = {
                "text": text,
                "payload": payloads[idx] if payloads and idx < len(payloads) else {},
            }

        writer.commit()

        if self._searcher is not None:
            self._searcher.close()
        self._searcher = self._index.searcher()
        logger.info("BM25 index built with %d documents", len(documents))

    def search_bm25(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search the BM25 index and return (doc_id, score) pairs."""
        if self._searcher is None or self._index is None:
            logger.warning("BM25 index not built")
            return []

        if not query or not query.strip():
            return []

        parser = QueryParser("content", schema=self._index.schema)
        try:
            q = parser.parse(query)
        except Exception as exc:
            logger.error("Failed to parse BM25 query '%s': %s", query, exc)
            return []

        results = self._searcher.search(q, limit=top_k)
        return [(r["doc_id"], r.score) for r in results]

    def rebuild_bm25(
        self,
        documents: List[str],
        payloads: List[Dict[str, Any]] | None = None,
    ) -> None:
        """Rebuild the BM25 index from scratch."""
        if self._searcher is not None:
            self._searcher.close()
            self._searcher = None
        self._index = None
        self.build_bm25_index(documents, payloads)

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------

    def reciprocal_rank_fusion(
        self,
        bm25_results: List[Tuple[str, float]],
        dense_results: List[ScoredPoint],
        k: int = 60,
    ) -> List[Tuple[str, float]]:
        """Fuse BM25 and dense results using Reciprocal Rank Fusion."""
        scores: Dict[str, float] = {}

        # BM25 contribution
        for rank, (doc_id, _) in enumerate(bm25_results, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

        # Dense contribution
        for rank, point in enumerate(dense_results, start=1):
            doc_id = point.id
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

        # Sort by fused score descending
        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return fused

    def weighted_fusion(
        self,
        bm25_results: List[Tuple[str, float]],
        dense_results: List[ScoredPoint],
        alpha: float = 0.3,
    ) -> List[Tuple[str, float]]:
        """Fuse BM25 and dense results using weighted score combination."""
        # Normalize scores to [0, 1]
        bm25_scores: Dict[str, float] = {}
        if bm25_results:
            max_bm25 = max(score for _, score in bm25_results) or 1.0
            bm25_scores = {doc_id: score / max_bm25 for doc_id, score in bm25_results}

        dense_scores: Dict[str, float] = {}
        if dense_results:
            max_dense = max(point.score for point in dense_results) or 1.0
            dense_scores = {point.id: point.score / max_dense for point in dense_results}

        all_ids = set(bm25_scores.keys()) | set(dense_scores.keys())
        fused = [
            (
                doc_id,
                alpha * bm25_scores.get(doc_id, 0.0)
                + (1 - alpha) * dense_scores.get(doc_id, 0.0),
            )
            for doc_id in all_ids
        ]
        fused.sort(key=lambda x: x[1], reverse=True)
        return fused

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        collection: str = "course_materials",
        top_k: int = 10,
        alpha: float | None = None,
        filters: Dict[str, Any] | None = None,
    ) -> List[ScoredPoint]:
        """Run hybrid search and return fused results."""
        alpha = alpha if alpha is not None else self.alpha

        # Run BM25 and dense search concurrently
        bm25_task = asyncio.get_event_loop().run_in_executor(
            None, self.search_bm25, query_text, top_k * 2
        )
        dense_task = self.vector_store.search(
            collection=collection,
            query_vector=query_vector,
            top_k=top_k * 2,
            filters=filters,
        )

        bm25_results, dense_results = await asyncio.gather(bm25_task, dense_task)

        # Edge case: one source empty
        if not bm25_results:
            logger.debug("BM25 returned no results; returning dense results only")
            return dense_results[:top_k]
        if not dense_results:
            logger.debug("Dense search returned no results; returning BM25 results only")
            return self._bm25_to_scored(bm25_results)[:top_k]

        # Very short query: boost BM25 weight
        if len(query_text.strip()) < 10:
            alpha = min(alpha + 0.2, 0.8)

        fused = self.weighted_fusion(bm25_results, dense_results, alpha=alpha)
        fused = fused[:top_k]

        return self._resolve_fused_results(fused)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bm25_to_scored(self, bm25_results: List[Tuple[str, float]]) -> List[ScoredPoint]:
        """Convert BM25 result tuples to ScoredPoint objects."""
        scored: List[ScoredPoint] = []
        for doc_id, score in bm25_results:
            payload = self._doc_map.get(doc_id, {}).get("payload", {})
            scored.append(ScoredPoint(id=doc_id, score=score, payload=payload))
        return scored

    def _resolve_fused_results(
        self, fused: List[Tuple[str, float]]
    ) -> List[ScoredPoint]:
        """Resolve fused doc IDs to ScoredPoint objects."""
        results: List[ScoredPoint] = []
        for doc_id, score in fused:
            payload = self._doc_map.get(doc_id, {}).get("payload", {})
            results.append(ScoredPoint(id=doc_id, score=score, payload=payload))
        return results


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_hybrid_search: HybridSearch | None = None


def get_hybrid_search(
    vector_store: QdrantStore | None = None,
    alpha: float = 0.3,
    rrf_k: int = 60,
) -> HybridSearch:
    """Return a singleton HybridSearch instance."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearch(
            vector_store=vector_store,
            alpha=alpha,
            rrf_k=rrf_k,
        )
    return _hybrid_search
