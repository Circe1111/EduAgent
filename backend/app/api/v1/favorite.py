import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.favorite import UserFavorite

logger = logging.getLogger(__name__)
router = APIRouter()


class FavoriteCreateRequest(BaseModel):
    question: str
    answer: str
    node_id: Optional[int] = None


class FavoriteResponse(BaseModel):
    id: int
    question: str
    answer: str
    node_id: Optional[int]
    created_at: str


class FavoriteCreateResponse(BaseModel):
    id: int
    created_at: str


@router.post("/favorites", response_model=FavoriteCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    request: FavoriteCreateRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a question-answer pair to user favorites."""
    try:
        favorite = UserFavorite(
            user_id=user_id,
            question=request.question,
            answer=request.answer,
            node_id=request.node_id,
        )
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)

        return FavoriteCreateResponse(
            id=favorite.id,
            created_at=favorite.created_at.isoformat() if favorite.created_at else "",
        )
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to create favorite")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create favorite: {str(exc)}",
        )


@router.get("/favorites", response_model=List[FavoriteResponse])
async def list_favorites(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all favorites for the authenticated user."""
    try:
        result = await db.execute(
            select(UserFavorite)
            .where(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.created_at.desc())
        )
        favorites = result.scalars().all()

        return [
            FavoriteResponse(
                id=fav.id,
                question=fav.question,
                answer=fav.answer,
                node_id=fav.node_id,
                created_at=fav.created_at.isoformat() if fav.created_at else "",
            )
            for fav in favorites
        ]
    except Exception as exc:
        logger.exception("Failed to list favorites")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list favorites: {str(exc)}",
        )


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: int,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a favorite by its ID."""
    try:
        result = await db.execute(
            select(UserFavorite).where(
                UserFavorite.id == favorite_id,
                UserFavorite.user_id == user_id,
            )
        )
        favorite = result.scalar_one_or_none()
        if favorite is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Favorite not found",
            )

        await db.delete(favorite)
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to delete favorite")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete favorite: {str(exc)}",
        )
