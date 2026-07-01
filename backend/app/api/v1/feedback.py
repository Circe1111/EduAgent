import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.feedback import Feedback as FeedbackDB
from app.db.models.session import Session as SessionDB
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackCreateRequest(BaseModel):
    session_id: str
    user_id: str
    resource_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default=None)
    is_adopted: bool = Field(default=False)


class FeedbackResponse(BaseModel):
    id: int
    session_id: str
    user_id: str
    resource_id: str
    rating: int
    comment: Optional[str]
    is_adopted: bool
    created_at: str


async def _resolve_db_user_id(user_id: str, db: AsyncSession) -> Optional[int]:
    """Resolve a string user identifier to the DB integer user id."""
    try:
        return int(user_id)
    except ValueError:
        result = await db.execute(select(User.id).where(User.username == user_id))
        return result.scalar_one_or_none()


async def _resolve_db_session_id(session_id: str, db: AsyncSession) -> Optional[int]:
    """Resolve a session UUID to the DB integer session id."""
    result = await db.execute(
        select(SessionDB.id).where(SessionDB.session_id == session_id)
    )
    return result.scalar_one_or_none()


@router.post("/feedback", status_code=status.HTTP_201_CREATED, response_model=FeedbackResponse)
async def create_feedback(
    request: FeedbackCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """
    Submit feedback on a generated resource.
    """
    try:
        db_user_id = await _resolve_db_user_id(request.user_id, db)
        if db_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        db_session_id = await _resolve_db_session_id(request.session_id, db)
        if db_session_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        feedback = FeedbackDB(
            session_id=db_session_id,
            user_id=db_user_id,
            resource_id=request.resource_id,
            rating=request.rating,
            comment=request.comment,
            is_adopted=request.is_adopted,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        return FeedbackResponse(
            id=feedback.id,
            session_id=request.session_id,
            user_id=request.user_id,
            resource_id=feedback.resource_id,
            rating=feedback.rating,
            comment=feedback.comment,
            is_adopted=feedback.is_adopted,
            created_at=feedback.created_at.isoformat() if feedback.created_at else "",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create feedback: {str(exc)}",
        )


@router.get("/feedback", response_model=List[FeedbackResponse])
async def list_feedback(
    session_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[FeedbackResponse]:
    """
    Retrieve feedback records for analysis.
    """
    try:
        query = select(FeedbackDB)

        if session_id is not None:
            db_session_id = await _resolve_db_session_id(session_id, db)
            if db_session_id is None:
                return []
            query = query.where(FeedbackDB.session_id == db_session_id)

        if user_id is not None:
            db_user_id = await _resolve_db_user_id(user_id, db)
            if db_user_id is None:
                return []
            query = query.where(FeedbackDB.user_id == db_user_id)

        result = await db.execute(query)
        feedbacks = result.scalars().all()

        responses = []
        for fb in feedbacks:
            # Resolve back to external IDs
            user_res = await db.execute(select(User.username).where(User.id == fb.user_id))
            username = user_res.scalar_one_or_none() or str(fb.user_id)
            session_res = await db.execute(
                select(SessionDB.session_id).where(SessionDB.id == fb.session_id)
            )
            session_uuid = session_res.scalar_one_or_none() or str(fb.session_id)

            responses.append(
                FeedbackResponse(
                    id=fb.id,
                    session_id=session_uuid,
                    user_id=username,
                    resource_id=fb.resource_id,
                    rating=fb.rating,
                    comment=fb.comment,
                    is_adopted=fb.is_adopted,
                    created_at=fb.created_at.isoformat() if fb.created_at else "",
                )
            )

        return responses
    except Exception as exc:
        logger.exception("Failed to list feedback")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list feedback: {str(exc)}",
        )
