import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.profile import StudentProfile as StudentProfileDB
from app.db.models.user import User
from app.models.profile import StudentProfile
from app.services.profile_service import ProfileService

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileUpdateRequest(BaseModel):
    learning_style: Optional[str] = Field(default=None)
    overall_difficulty: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    knowledge_points: Optional[Dict[str, float]] = Field(default=None)


async def _resolve_db_user_id(user_id: str, db: AsyncSession) -> Optional[int]:
    """Resolve a string user identifier to the DB integer user id."""
    try:
        return int(user_id)
    except ValueError:
        result = await db.execute(select(User.id).where(User.username == user_id))
        return result.scalar_one_or_none()


@router.get("/profile/{user_id}", response_model=StudentProfile)
async def get_profile(user_id: str) -> StudentProfile:
    """
    Retrieve a student's profile by user identifier.
    """
    try:
        service = ProfileService()
        return await service.get_profile(user_id)
    except Exception as exc:
        logger.exception("Failed to retrieve profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve profile: {str(exc)}",
        )


@router.put("/profile/{user_id}", response_model=StudentProfile)
async def update_profile(
    user_id: str,
    update: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    """
    Update a student's profile fields.
    """
    try:
        db_user_id = await _resolve_db_user_id(user_id, db)
        if db_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        result = await db.execute(
            select(StudentProfileDB).where(StudentProfileDB.user_id == db_user_id)
        )
        db_profile = result.scalar_one_or_none()

        if db_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

        if update.learning_style is not None:
            db_profile.learning_style = update.learning_style
        if update.overall_difficulty is not None:
            db_profile.overall_difficulty = update.overall_difficulty
        if update.knowledge_points is not None:
            current = dict(db_profile.knowledge_points or {})
            current.update(update.knowledge_points)
            db_profile.knowledge_points = current

        await db.commit()
        await db.refresh(db_profile)

        return StudentProfile(
            user_id=user_id,
            knowledge_points=dict(db_profile.knowledge_points or {}),
            overall_difficulty=db_profile.overall_difficulty,
            learning_style=db_profile.learning_style,
            session_count=db_profile.session_count or 0,
            updated_at=db_profile.last_active,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(exc)}",
        )
