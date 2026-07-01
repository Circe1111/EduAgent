import logging
import uuid
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.agents.router import AgentOrchestrator
from app.core.database import async_session_factory, get_db
from app.db.models.session import Session as SessionDB
from app.db.models.user import User
from app.models.session_context import SessionContext
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    query: str
    knowledge_points: Optional[List[str]] = Field(default=None)
    difficulty: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)


async def _resolve_db_user_id(user_id: str, db: AsyncSession) -> int:
    """Resolve a string user identifier to the DB integer user id."""
    try:
        return int(user_id)
    except ValueError:
        result = await db.execute(select(User.id).where(User.username == user_id))
        db_user_id = result.scalar_one_or_none()
        if db_user_id is None:
            user = User(username=user_id)
            db.add(user)
            await db.flush()
            db_user_id = user.id
        return db_user_id


async def _save_session(context: SessionContext) -> None:
    """Persist session context to the database in a background task."""
    async with async_session_factory() as db:
        try:
            db_user_id = await _resolve_db_user_id(context.user_id, db)
            messages = []
            if context.task_spec and "query" in context.task_spec:
                messages.append({"role": "user", "content": context.task_spec["query"]})
            if context.generated_content:
                messages.append(
                    {
                        "role": "assistant",
                        "content": context.generated_content.content,
                        "metadata": context.generated_content.metadata,
                    }
                )
            db_session = SessionDB(
                session_id=context.session_id,
                user_id=db_user_id,
                messages=messages,
                context_summary=context.history_summary,
            )
            db.add(db_session)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Failed to save session to database")


async def _stream_content(content: str) -> AsyncGenerator[str, None]:
    """Stream content word-by-word as SSE events."""
    words = content.split(" ")
    for i, word in enumerate(words):
        suffix = " " if i < len(words) - 1 else ""
        yield f"data: {word}{suffix}\n\n"
    yield "data: [DONE]\n\n"


GREETINGS = {"你好", "hello", "hi", "在吗", "在不在", "您好", "hey", "上午好", "下午好", "晚上好"}


def _is_greeting(query: str) -> bool:
    """Check if query is a greeting, return short response directly."""
    q = query.strip().lower()
    for g in GREETINGS:
        if g in q or q == g:
            return True
    return False


@router.post("/chat", response_model=SessionContext)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SessionContext:
    """
    Run the full agent orchestration pipeline for a chat query.
    """
    try:
        # Greeting short-circuit
        if _is_greeting(request.query):
            from app.models.content import GeneratedContent
            return SessionContext(
                session_id=request.session_id,
                user_id=request.user_id,
                task_spec={"query": request.query},
                generated_content=GeneratedContent(
                    content="你好！我是 EduAgent，你的 Python 学习助手。我可以帮你解答问题、生成练习题、规划学习路径。有什么想学的吗？",
                    content_type="greeting",
                    confidence=1.0,
                ),
                metadata={"from_cache": False, "intent_time": 0},
            )

        context = SessionContext(
            session_id=request.session_id,
            user_id=request.user_id,
            task_spec={"query": request.query},
            knowledge_points=request.knowledge_points or [],
            difficulty=request.difficulty if request.difficulty is not None else 0.5,
        )

        profile_service = ProfileService()
        student_profile = await profile_service.get_or_create_profile(request.user_id)
        context.student_profile = student_profile

        orchestrator = AgentOrchestrator()
        final_context = await orchestrator.run(context)

        background_tasks.add_task(_save_session, final_context)

        return final_context
    except Exception as exc:
        logger.exception("Chat endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(exc)}",
        )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Run the full agent orchestration pipeline and stream generated content via SSE.
    """
    try:
        context = SessionContext(
            session_id=request.session_id,
            user_id=request.user_id,
            task_spec={"query": request.query},
            knowledge_points=request.knowledge_points or [],
            difficulty=request.difficulty if request.difficulty is not None else 0.5,
        )

        profile_service = ProfileService()
        student_profile = await profile_service.get_or_create_profile(request.user_id)
        context.student_profile = student_profile

        orchestrator = AgentOrchestrator()
        final_context = await orchestrator.run(context)

        background_tasks.add_task(_save_session, final_context)

        if final_context.generated_content and final_context.generated_content.content:
            return StreamingResponse(
                _stream_content(final_context.generated_content.content),
                media_type="text/event-stream",
            )
        else:
            return StreamingResponse(
                _stream_content("No content generated."),
                media_type="text/event-stream",
            )
    except Exception as exc:
        logger.exception("Chat stream endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat stream processing failed: {str(exc)}",
        )
