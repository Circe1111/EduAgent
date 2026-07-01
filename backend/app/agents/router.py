import logging
import time
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.models.session_context import SessionContext

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    LangGraph-based orchestrator for the EduAgent 2.0 multi-agent pipeline.

    Graph flow (Phase 1):
        intent -> retrieve -> generate -> critic -> (pass: plan) | (fail: refine)

    The critic loop allows up to ``max_retries`` refinement passes before
    falling through to the planner with a ``low_confidence`` flag.
    """

    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries
        self._graph: Any | None = None

    def _build_graph(self) -> Any:
        """
        Construct the LangGraph StateGraph.

        Agents are imported lazily here to avoid circular imports at module level.
        """
        from app.agents.critic import CritiqueAgent
        from app.agents.generator import ContentGenerationAgent
        from app.agents.intent import IntentAnalysisAgent
        from app.agents.planner import LearningPathAgent
        from app.agents.refiner import RefinerAgent
        from app.agents.retriever import RetrievalAgent

        intent_agent = IntentAnalysisAgent()
        retrieval_agent = RetrievalAgent()
        generator_agent = ContentGenerationAgent()
        critic_agent = CritiqueAgent()
        refiner_agent = RefinerAgent()
        planner_agent = LearningPathAgent()

        workflow = StateGraph(SessionContext)

        # ------------------------------------------------------------------
        # Node wrappers (timing + error handling)
        # ------------------------------------------------------------------

        async def intent_node(context: SessionContext) -> SessionContext:
            start = time.time()
            try:
                result = await intent_agent.process(context)
            except Exception as exc:
                logger.exception("Intent node failed")
                result = await intent_agent.handle_error(context, exc)
            result.metadata["intent_time"] = round(time.time() - start, 3)
            return result

        async def retrieve_node(context: SessionContext) -> SessionContext:
            start = time.time()
            try:
                result = await retrieval_agent.process(context)
            except Exception as exc:
                logger.exception("Retrieve node failed")
                result = await retrieval_agent.handle_error(context, exc)
            result.metadata["retrieve_time"] = round(time.time() - start, 3)
            return result

        async def generate_node(context: SessionContext) -> SessionContext:
            start = time.time()
            try:
                result = await generator_agent.process(context)
            except Exception as exc:
                logger.exception("Generate node failed")
                result = await generator_agent.handle_error(context, exc)
            result.metadata["generate_time"] = round(time.time() - start, 3)
            return result

        async def critic_node(context: SessionContext) -> SessionContext:
            start = time.time()
            try:
                result = await critic_agent.process(context)
            except Exception as exc:
                logger.exception("Critic node failed")
                result = await critic_agent.handle_error(context, exc)
            result.metadata["critic_time"] = round(time.time() - start, 3)
            return result

        async def refine_node(context: SessionContext) -> SessionContext:
            start = time.time()
            try:
                result = await refiner_agent.process(context)
            except Exception as exc:
                logger.exception("Refine node failed")
                result = await refiner_agent.handle_error(context, exc)
            result.metadata["refine_time"] = round(time.time() - start, 3)
            return result

        async def plan_node(context: SessionContext) -> SessionContext:
            start = time.time()
            try:
                result = await planner_agent.process(context)
            except Exception as exc:
                logger.exception("Plan node failed")
                result = await planner_agent.handle_error(context, exc)
            result.metadata["plan_time"] = round(time.time() - start, 3)
            return result

        # ------------------------------------------------------------------
        # Graph topology
        # ------------------------------------------------------------------

        workflow.add_node("intent", intent_node)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)
        workflow.add_node("critic", critic_node)
        workflow.add_node("refine", refine_node)
        workflow.add_node("plan", plan_node)

        workflow.set_entry_point("intent")
        workflow.add_edge("intent", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", "critic")

        # Conditional edge: critic -> refine (targeted fix) or plan
        def critic_decision(context: SessionContext) -> str:
            retry_count = context.metadata.get("critique_retry_count", 0)
            if context.critique_result is not None and not context.critique_result.passed:
                if retry_count < self.max_retries:
                    context.metadata["critique_retry_count"] = retry_count + 1
                    logger.info(
                        "Critic failed (retry %d/%d); routing to refine",
                        retry_count + 1,
                        self.max_retries,
                    )
                    return "refine"
                # Max retries exhausted
                logger.warning(
                    "Critic failed after %d retries; proceeding with low confidence",
                    self.max_retries,
                )
                context.metadata["low_confidence"] = True
            return "plan"

        workflow.add_conditional_edges(
            "critic",
            critic_decision,
            {
                "refine": "refine",
                "plan": "plan",
            },
        )

        # After refinement, route back to critic for re-evaluation
        workflow.add_edge("refine", "critic")

        workflow.add_edge("plan", END)

        self._graph = workflow.compile()
        return self._graph

    async def run(self, initial_context: SessionContext) -> SessionContext:
        """
        Execute the full agent pipeline.

        Args:
            initial_context: The starting session context.

        Returns:
            The final SessionContext after all agents have run.
        """
        if self._graph is None:
            self._build_graph()

        # ------------------------------------------------------------------
        # Semantic cache check
        # ------------------------------------------------------------------
        query = None
        if initial_context.task_spec and "query" in initial_context.task_spec:
            query = initial_context.task_spec["query"]

        if query:
            from app.services.cache_service import SemanticCache
            from app.core.database import create_redis_pool
            from app.rag.embeddings import get_embedding_service

            redis_client = create_redis_pool()
            embedding_service = get_embedding_service()
            cache = SemanticCache(
                redis_client=redis_client,
                embedding_service=embedding_service,
            )

            try:
                cached = await cache.get(query, initial_context.user_id)
                if cached:
                    logger.info(
                        "Semantic cache HIT for user=%s", initial_context.user_id
                    )
                    result_dict = cached["result"]
                    restored_context = SessionContext.model_validate(result_dict)
                    restored_context.metadata["from_cache"] = True
                    restored_context.metadata["cache_similarity"] = cached.get(
                        "similarity"
                    )
                    return restored_context
            except Exception:
                logger.exception("Semantic cache lookup failed, proceeding with graph")

        # ------------------------------------------------------------------
        # Run graph
        # ------------------------------------------------------------------
        try:
            final_state = await self._graph.ainvoke(initial_context)
        except Exception as exc:
            logger.exception("Graph execution failed")
            initial_context.add_error(
                f"Orchestrator: {type(exc).__name__}: {str(exc)}"
            )
            return initial_context

        # Convert graph output (dict) back to SessionContext
        if isinstance(final_state, dict):
            try:
                final_state = SessionContext.model_validate(final_state)
            except Exception as exc:
                logger.exception("Failed to convert graph output to SessionContext")
                initial_context.add_error(f"Orchestrator: state conversion failed: {exc}")
                return initial_context

        # ------------------------------------------------------------------
        # Cache successful results
        # ------------------------------------------------------------------
        if query and final_state.is_valid():
            is_path_planning = (
                final_state.task_intent is not None
                and final_state.task_intent.task_type.value == "path_planning"
            )
            has_content = (
                final_state.generated_content is not None
                and bool(final_state.generated_content.content)
            )

            if not is_path_planning and has_content:
                from app.services.cache_service import SemanticCache
                from app.core.database import create_redis_pool
                from app.rag.embeddings import get_embedding_service

                redis_client = create_redis_pool()
                embedding_service = get_embedding_service()
                cache = SemanticCache(
                    redis_client=redis_client,
                    embedding_service=embedding_service,
                )

                try:
                    cacheable_result = final_state.to_dict()
                    await cache.set(query, initial_context.user_id, cacheable_result)
                except Exception:
                    logger.exception("Semantic cache store failed")

        return final_state
