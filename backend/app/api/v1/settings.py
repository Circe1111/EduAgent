import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.auth import hash_password, verify_password
from app.core.database import get_db
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    daily_goal: Optional[int] = None
    theme: Optional[str] = None


class AccountDeleteRequest(BaseModel):
    password: str


class MessageResponse(BaseModel):
    message: str


@router.put("/settings/password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify old password and update to new password."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.password_hash is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password not set. Please set a password first.",
            )

        if not verify_password(request.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Old password is incorrect",
            )

        user.password_hash = hash_password(request.new_password)
        await db.commit()

        return MessageResponse(message="Mi Ma Geng Xin Cheng Gong")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to change password")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(exc)}",
        )


@router.put("/settings/profile", response_model=MessageResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings like daily goal and theme."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if request.daily_goal is not None:
            if request.daily_goal < 1 or request.daily_goal > 480:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Daily goal must be between 1 and 480 minutes",
                )
            user.daily_goal = request.daily_goal

        if request.theme is not None:
            valid_themes = {"light", "dark", "auto"}
            if request.theme not in valid_themes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Theme must be one of: {', '.join(sorted(valid_themes))}",
                )
            user.theme = request.theme

        await db.commit()

        return MessageResponse(message="She Zhi Geng Xin Cheng Gong")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to update profile settings")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile settings: {str(exc)}",
        )


@router.post("/settings/clear-cache", response_model=MessageResponse)
async def clear_cache(
    user_id: int = Depends(get_current_user),
):
    """Clear user's local cache (stub endpoint)."""
    return MessageResponse(message="Huan Cun Yi Qing Chu")


@router.delete("/settings/account", response_model=MessageResponse)
async def delete_account(
    request: AccountDeleteRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete user account after password confirmation."""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.password_hash is not None:
            if not verify_password(request.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password is incorrect",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete account: no password set",
            )

        await db.delete(user)
        await db.commit()

        return MessageResponse(message="Zhang Hao Yi Shan Chu")
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to delete account")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(exc)}",
        )
