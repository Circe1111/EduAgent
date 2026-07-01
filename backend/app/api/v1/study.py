import logging
from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.db.models.badge import UserBadge
from app.db.models.learning_record import LearningRecord
from app.db.models.study_record import StudyRecord
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class StudyLogRequest(BaseModel):
    node_id: int
    duration_seconds: int


class StudyLogResponse(BaseModel):
    id: int
    duration_seconds: int
    total_today: int


class StudyStatsResponse(BaseModel):
    total_minutes: int
    today_minutes: int
    total_sessions: int
    today_sessions: int


class CalendarEntry(BaseModel):
    study_date: str
    total_minutes: int


async def _check_and_award_study_badges(
    user_id: int,
    db: AsyncSession,
) -> list:
    """Check badge conditions after study log and award any newly earned badges."""
    newly_earned = []

    # -- FIRST_COMPLETE: first study record ever --
    already_has = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_code == "FIRST_COMPLETE",
        )
    )
    if already_has.scalar_one_or_none() is None:
        # Check if first record (user has at least one record)
        count_result = await db.execute(
            select(func.count(StudyRecord.id)).where(StudyRecord.user_id == user_id)
        )
        record_count = count_result.scalar() or 0
        if record_count >= 1:
            badge = UserBadge(
                user_id=user_id,
                badge_code="FIRST_COMPLETE",
                badge_name="Po Zhan Zhe",
            )
            db.add(badge)
            newly_earned.append("FIRST_COMPLETE")

    # -- STREAK_7: study >= 15 minutes for 7 consecutive days --
    already_has = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_code == "STREAK_7",
        )
    )
    if already_has.scalar_one_or_none() is None:
        # Check the last 7 dates
        today = date.today()
        dates_to_check = [today - timedelta(days=i) for i in range(7)]
        for d in dates_to_check:
            result = await db.execute(
                select(func.coalesce(func.sum(StudyRecord.duration_seconds), 0))
                .where(
                    StudyRecord.user_id == user_id,
                    StudyRecord.study_date == d,
                )
            )
            total_secs = result.scalar() or 0
            if total_secs < 900:  # 15 minutes
                break
        else:
            # All 7 days have >= 15 min
            badge = UserBadge(
                user_id=user_id,
                badge_code="STREAK_7",
                badge_name="Lian Ji Da Ren",
            )
            db.add(badge)
            newly_earned.append("STREAK_7")

    return newly_earned


@router.post("/study/log", response_model=StudyLogResponse)
async def log_study(
    request: StudyLogRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a study session record for the authenticated user."""
    try:
        record = StudyRecord(
            user_id=user_id,
            node_id=request.node_id,
            duration_seconds=request.duration_seconds,
            study_date=date.today(),
        )
        db.add(record)
        await db.flush()

        # Get total today
        result = await db.execute(
            select(func.coalesce(func.sum(StudyRecord.duration_seconds), 0))
            .where(
                StudyRecord.user_id == user_id,
                StudyRecord.study_date == date.today(),
            )
        )
        total_today = result.scalar() or 0

        # Check badge conditions
        await _check_and_award_study_badges(user_id, db)

        await db.commit()
        await db.refresh(record)

        return StudyLogResponse(
            id=record.id,
            duration_seconds=record.duration_seconds,
            total_today=total_today,
        )
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to log study record")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log study record: {str(exc)}",
        )


@router.get("/study/stats", response_model=StudyStatsResponse)
async def get_study_stats(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated study statistics for the authenticated user."""
    try:
        # Total all-time stats
        total_result = await db.execute(
            select(
                func.coalesce(func.sum(StudyRecord.duration_seconds), 0),
                func.count(StudyRecord.id),
            ).where(StudyRecord.user_id == user_id)
        )
        total_seconds, total_sessions = total_result.one()

        # Today stats
        today_result = await db.execute(
            select(
                func.coalesce(func.sum(StudyRecord.duration_seconds), 0),
                func.count(StudyRecord.id),
            ).where(
                StudyRecord.user_id == user_id,
                StudyRecord.study_date == date.today(),
            )
        )
        today_seconds, today_sessions = today_result.one()

        return StudyStatsResponse(
            total_minutes=total_seconds // 60,
            today_minutes=today_seconds // 60,
            total_sessions=total_sessions,
            today_sessions=today_sessions,
        )
    except Exception as exc:
        logger.exception("Failed to get study stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get study stats: {str(exc)}",
        )


@router.get("/study/calendar", response_model=List[CalendarEntry])
async def get_calendar(
    days: int = Query(default=90, ge=1, le=365, description="Number of days to look back"),
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return study duration per day for the last N days (heatmap data).

    Primary source: learning_records table (duration_minutes).
    Fallback: study_records table (convert seconds to minutes).
    """
    try:
        since = date.today() - timedelta(days=days)

        user_result = await db.execute(
            select(User.username).where(User.id == user_id)
        )
        user_row = user_result.one_or_none()

        if user_row is not None:
            student_id = user_row[0]
            result = await db.execute(
                select(
                    LearningRecord.study_date,
                    func.coalesce(func.sum(LearningRecord.duration_minutes), 0),
                )
                .where(
                    LearningRecord.user_id == student_id,
                    LearningRecord.study_date >= since,
                )
                .group_by(LearningRecord.study_date)
                .order_by(LearningRecord.study_date)
            )
            rows = result.all()
            if rows:
                return [
                    CalendarEntry(study_date=str(row[0]), total_minutes=row[1])
                    for row in rows
                ]

        result = await db.execute(
            select(
                StudyRecord.study_date,
                func.coalesce(func.sum(StudyRecord.duration_seconds), 0),
            )
            .where(
                StudyRecord.user_id == user_id,
                StudyRecord.study_date >= since,
            )
            .group_by(StudyRecord.study_date)
            .order_by(StudyRecord.study_date)
        )
        rows = result.all()
        return [
            CalendarEntry(study_date=str(row[0]), total_minutes=row[1] // 60)
            for row in rows
        ]
    except Exception as exc:
        logger.exception("Failed to get study calendar")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get study calendar: {str(exc)}",
        )


# ── Node progress (learning path completion) ────────────────────────────────


class NodeProgress(BaseModel):
    chapter: str
    total_sessions: int
    avg_score: float
    avg_correct_rate: float
    total_problems: int
    total_minutes: int
    status: str  # "completed", "in_progress", "pending"


class NodeProgressResponse(BaseModel):
    nodes: List[NodeProgress]


@router.get("/study/node-progress", response_model=NodeProgressResponse)
async def get_node_progress(
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return learning progress per chapter from learning_records."""
    user_result = await db.execute(select(User.username).where(User.id == user_id))
    row = user_result.one_or_none()
    if not row:
        return NodeProgressResponse(nodes=[])

    student_id = row[0]
    result = await db.execute(
        select(
            LearningRecord.chapter,
            func.count(LearningRecord.id),
            func.avg(LearningRecord.score),
            func.avg(LearningRecord.correct_rate),
            func.sum(LearningRecord.problems_done),
            func.sum(LearningRecord.duration_minutes),
        )
        .where(LearningRecord.user_id == student_id)
        .group_by(LearningRecord.chapter)
        .order_by(LearningRecord.chapter)
    )
    rows = result.all()
    nodes = []
    for r in rows:
        avg_score = round(float(r[2]), 1) if r[2] else 0.0
        if avg_score >= 60:
            status = "completed"
        elif avg_score > 0:
            status = "in_progress"
        else:
            status = "pending"
        nodes.append(NodeProgress(
            chapter=r[0],
            total_sessions=r[1],
            avg_score=avg_score,
            avg_correct_rate=round(float(r[3]), 2) if r[3] else 0.0,
            total_problems=r[4] or 0,
            total_minutes=r[5] or 0,
            status=status,
        ))

    return NodeProgressResponse(nodes=nodes)
