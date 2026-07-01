from typing import Any, Dict, List

from app.agents.base import BaseAgent
from app.models.session_context import SessionContext
from app.rag.embeddings import EmbeddingService, get_embedding_service
from app.rag.hybrid_search import HybridSearch, get_hybrid_search


class RetrievalAgent(BaseAgent):
    """
    Agent that retrieves relevant knowledge chunks based on the
    student's intent and profile.
    """

    name = "retrieval"

    def __init__(
        self,
        search: HybridSearch | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.search = search or get_hybrid_search()
        self.embedding_service = embedding_service or get_embedding_service()

    async def process(self, context: SessionContext) -> SessionContext:
        if not await self.validate_input(context):
            return context.add_error("RetrievalAgent: invalid input context")

        if context.task_intent is None:
            return context.add_error("RetrievalAgent: missing task_intent")

        try:
            query = " ".join(context.task_intent.knowledge_points)
            if context.task_spec and isinstance(context.task_spec, dict):
                explicit_query = context.task_spec.get("query")
                if explicit_query:
                    query = explicit_query

            # Determine student difficulty for reranking
            student_difficulty = context.difficulty
            if context.student_profile is not None:
                student_difficulty = context.student_profile.overall_difficulty

            # Embed query for dense search
            query_vector = await self.embedding_service.embed_query(query)

            # Run hybrid search
            scored_points = await self.search.hybrid_search(
                query_text=query,
                query_vector=query_vector,
                top_k=10,
            )

            # Convert ScoredPoint to plain dicts and rerank/filter
            filtered: List[Dict[str, Any]] = []
            for point in scored_points:
                payload = point.payload or {}
                result = {
                    "text": payload.get("content") or payload.get("text", ""),
                    "source": payload.get("source", "未知"),
                    "chapter": payload.get("chapter", "未知"),
                    "knowledge_point": payload.get("heading") or payload.get("knowledge_point", ""),
                    "score": point.score,
                    "difficulty": payload.get("difficulty", 0.5),
                }

                # Rerank by difficulty proximity
                diff_distance = abs(result["difficulty"] - student_difficulty)
                result["rerank_score"] = result["score"] * (1.0 - diff_distance * 0.5)

                # Filter by knowledge-point relevance
                kp_match = any(
                    kp in result["text"] or kp in result["knowledge_point"]
                    for kp in context.task_intent.knowledge_points
                )
                if kp_match or not context.task_intent.knowledge_points:
                    filtered.append(result)

            # Sort by rerank score descending
            filtered.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

            # Top-k
            top_k = 5
            context.retrieval_results = filtered[:top_k]

            if not context.retrieval_results:
                context.metadata["retrieval_empty"] = True

        except Exception as exc:
            context = await self.handle_error(context, exc)
            context.metadata["retrieval_empty"] = True

        return context
