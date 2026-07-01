import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.badge import UserBadge
from app.db.models.quiz_history import QuizHistory
from app.db.models.study_record import StudyRecord

logger = logging.getLogger(__name__)
router = APIRouter()

# Definition of all possible badges
POSSIBLE_BADGES = [
    {
        "code": "FIRST_COMPLETE",
        "name": "Po Zhan Zhe",
        "condition": "Wan Cheng Di Yi Ge Jie Dian Xue Xi",
    },
    {
        "code": "STREAK_7",
        "name": "Lian Ji Da Ren",
        "condition": "Lian Xu 7 Tian Xue Xi ≥ 15 Fen Zhong",
    },
    {
        "code": "SCHOLAR",
        "name": "Xue Ba",
        "condition": "Ren Yi 3 Ge Jie Dian Ce Yan ≥ 90 Fen",
    },
]


class BadgeInfo(BaseModel):
    code: str
    name: str
    condition: str
    earned: bool
    earned_at: Optional[str] = None


class BadgeCheckResponse(BaseModel):
    newly_earned: List[str]


@router.get("/badges", response_model=List[BadgeInfo])
async def list_badges(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all possible badges with the user's earned status for each."""
    try:
        # Get all badges the user has earned
        result = await db.execute(
            select(UserBadge).where(UserBadge.user_id == user_id)
        )
        earned_badges = {b.badge_code: b for b in result.scalars().all()}

        return [
            BadgeInfo(
                code=badge["code"],
                name=badge["name"],
                condition=badge["condition"],
                earned=badge["code"] in earned_badges,
                earned_at=(
                    earned_badges[badge["code"]].earned_at.isoformat()
                    if badge["code"] in earned_badges and earned_badges[badge["code"]].earned_at
                    else None
                ),
            )
            for badge in POSSIBLE_BADGES
        ]
    except Exception as exc:
        logger.exception("Failed to list badges")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list badges: {str(exc)}",
        )


async def _check_first_complete(user_id: int, db: AsyncSession) -> bool:
    """Check and award FIRST_COMPLETE badge."""
    already = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_code == "FIRST_COMPLETE",
        )
    )
    if already.scalar_one_or_none() is not None:
        return False

    count_result = await db.execute(
        select(func.count(StudyRecord.id)).where(StudyRecord.user_id == user_id)
    )
    if (count_result.scalar() or 0) >= 1:
        badge = UserBadge(
            user_id=user_id,
            badge_code="FIRST_COMPLETE",
            badge_name="Po Zhan Zhe",
        )
        db.add(badge)
        return True
    return False


async def _check_streak_7(user_id: int, db: AsyncSession) -> bool:
    """Check and award STREAK_7 badge."""
    already = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_code == "STREAK_7",
        )
    )
    if already.scalar_one_or_none() is not None:
        return False

    today = date.today()
    for i in range(7):
        d = today - timedelta(days=i)
        result = await db.execute(
            select(func.coalesce(func.sum(StudyRecord.duration_seconds), 0))
            .where(
                StudyRecord.user_id == user_id,
                StudyRecord.study_date == d,
            )
        )
        if (result.scalar() or 0) < 900:  # 15 minutes in seconds
            return False

    badge = UserBadge(
        user_id=user_id,
        badge_code="STREAK_7",
        badge_name="Lian Ji Da Ren",
    )
    db.add(badge)
    return True


async def _check_scholar(user_id: int, db: AsyncSession) -> bool:
    """Check and award SCHOLAR badge."""
    already = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_code == "SCHOLAR",
        )
    )
    if already.scalar_one_or_none() is not None:
        return False

    # Get distinct nodes with quiz records
    nodes_result = await db.execute(
        select(QuizHistory.node_id)
        .where(QuizHistory.user_id == user_id)
        .distinct()
    )
    node_ids = [row[0] for row in nodes_result.all()]

    high_score_count = 0
    for nid in node_ids:
        # Get last 5 records (most recent attempt) for this node
        last_5 = await db.execute(
            select(QuizHistory.is_correct)
            .where(
                QuizHistory.user_id == user_id,
                QuizHistory.node_id == nid,
            )
            .order_by(QuizHistory.created_at.desc())
            .limit(5)
        )
        records = last_5.all()
        if len(records) < 5:
            continue
        correct = sum(1 for r in records if r[0])
        if correct / 5 * 100 >= 90:
            high_score_count += 1

    if high_score_count >= 3:
        badge = UserBadge(
            user_id=user_id,
            badge_code="SCHOLAR",
            badge_name="Xue Ba",
        )
        db.add(badge)
        return True
    return False


@router.get("/badges/check", response_model=BadgeCheckResponse)
async def check_badges(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check all badge conditions and award any newly earned badges."""
    try:
        newly_earned = []

        if await _check_first_complete(user_id, db):
            newly_earned.append("FIRST_COMPLETE")
        if await _check_streak_7(user_id, db):
            newly_earned.append("STREAK_7")
        if await _check_scholar(user_id, db):
            newly_earned.append("SCHOLAR")

        if newly_earned:
            await db.commit()

        return BadgeCheckResponse(newly_earned=newly_earned)
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to check badges")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check badges: {str(exc)}",
        )
