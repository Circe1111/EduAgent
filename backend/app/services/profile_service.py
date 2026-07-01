from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.profile import StudentProfile as StudentProfileDB
from app.db.models.user import User
from app.models.profile import StudentProfile


class ProfileService:
    """
    Pure-logic profile service.

    Handles all student profile CRUD and analytics without any LLM calls.
    All DB operations go through ``get_db()`` async sessions.
    """

    async def _resolve_db_user_id(
        self, user_id: str, session: AsyncSession
    ) -> Optional[int]:
        """
        Resolve a string user identifier to the DB integer user id.

        Tries int conversion first, then falls back to username lookup.
        """
        try:
            return int(user_id)
        except ValueError:
            result = await session.execute(
                select(User.id).where(User.username == user_id)
            )
            return result.scalar_one_or_none()

    def _to_pydantic(
        self, db_profile: StudentProfileDB, user_id_str: str
    ) -> StudentProfile:
        """Convert a DB profile row to the Pydantic StudentProfile model."""
        return StudentProfile(
            user_id=user_id_str,
            knowledge_points=dict(db_profile.knowledge_points or {}),
            overall_difficulty=db_profile.overall_difficulty,
            learning_style=db_profile.learning_style,
            session_count=db_profile.session_count or 0,
            updated_at=db_profile.last_active or datetime.utcnow(),
        )

    async def get_or_create_profile(self, user_id: str) -> StudentProfile:
        """
        Retrieve an existing profile or create a default one.

        Args:
            user_id: External string identifier for the student.

        Returns:
            The student's profile (Pydantic model).
        """
        async for session in get_db():
            db_user_id = await self._resolve_db_user_id(user_id, session)

            if db_user_id is None:
                # Create a new user row first
                user = User(username=user_id)
                session.add(user)
                await session.flush()
                db_user_id = user.id

            result = await session.execute(
                select(StudentProfileDB).where(
                    StudentProfileDB.user_id == db_user_id
                )
            )
            db_profile = result.scalar_one_or_none()

            if db_profile is None:
                db_profile = StudentProfileDB(
                    user_id=db_user_id,
                    knowledge_points={},
                    overall_difficulty=0.5,
                    learning_style="adaptive",
                    session_count=0,
                    accuracy=0.0,
                )
                session.add(db_profile)
                # Let get_db() commit on generator exit

            return self._to_pydantic(db_profile, user_id)

    async def update_profile_after_interaction(
        self,
        user_id: str,
        knowledge_point: str,
        is_correct: bool,
        difficulty: float,
    ) -> None:
        """
        Update profile after a single interaction.

        Applies:
        - Sliding weighted average for accuracy
        - Session count increment
        - Difficulty preference drift
        - Knowledge point mastery nudge
        - Learning style heuristic update

        Args:
            user_id: Student identifier.
            knowledge_point: The knowledge point tested/taught.
            is_correct: Whether the student answered correctly.
            difficulty: The difficulty level of the interaction (0-1).
        """
        async for session in get_db():
            db_user_id = await self._resolve_db_user_id(user_id, session)
            if db_user_id is None:
                return

            result = await session.execute(
                select(StudentProfileDB).where(
                    StudentProfileDB.user_id == db_user_id
                )
            )
            db_profile = result.scalar_one_or_none()
            if db_profile is None:
                return

            # 1. Accuracy sliding weighted average
            current_score = 1.0 if is_correct else 0.0
            old_accuracy = db_profile.accuracy or 0.0
            db_profile.accuracy = 0.7 * old_accuracy + 0.3 * current_score

            # 2. Session count
            db_profile.session_count = (db_profile.session_count or 0) + 1

            # 3. Difficulty preference drift
            old_difficulty = db_profile.overall_difficulty or 0.5
            db_profile.overall_difficulty = 0.8 * old_difficulty + 0.2 * difficulty

            # 4. Knowledge mastery nudge
            kp_dict: dict = dict(db_profile.knowledge_points or {})
            old_mastery = kp_dict.get(knowledge_point, 0.0)
            delta = 0.1 if is_correct else -0.05
            kp_dict[knowledge_point] = max(0.0, min(1.0, old_mastery + delta))
            db_profile.knowledge_points = kp_dict

            # 5. Learning style heuristic (after enough data)
            if db_profile.session_count > 5:
                acc = db_profile.accuracy
                if acc > 0.8:
                    db_profile.learning_style = "advanced"
                elif acc < 0.4:
                    db_profile.learning_style = "guided"
                else:
                    db_profile.learning_style = "adaptive"

    async def update_mastery(
        self, user_id: str, knowledge_point: str, score: float
    ) -> None:
        """
        Directly update mastery for a knowledge point.

        Uses a weighted blend of old and new score.

        Args:
            user_id: Student identifier.
            knowledge_point: Knowledge point name.
            score: New observed score (0.0-1.0).
        """
        async for session in get_db():
            db_user_id = await self._resolve_db_user_id(user_id, session)
            if db_user_id is None:
                return

            result = await session.execute(
                select(StudentProfileDB).where(
                    StudentProfileDB.user_id == db_user_id
                )
            )
            db_profile = result.scalar_one_or_none()
            if db_profile is None:
                return

            kp_dict: dict = dict(db_profile.knowledge_points or {})
            old_mastery = kp_dict.get(knowledge_point, 0.0)
            blended = max(0.0, min(1.0, 0.6 * old_mastery + 0.4 * score))
            kp_dict[knowledge_point] = blended
            db_profile.knowledge_points = kp_dict

    async def get_profile(self, user_id: str) -> StudentProfile:
        """
        Get a student's profile.

        Args:
            user_id: Student identifier.

        Returns:
            The student's profile.
        """
        return await self.get_or_create_profile(user_id)

    async def calculate_accuracy(self, profile: StudentProfile) -> float:
        """
        Calculate average mastery accuracy from the profile.

        Args:
            profile: The student's Pydantic profile.

        Returns:
            Average mastery score (0.0-1.0), or 0.0 if no data.
        """
        if not profile.knowledge_points:
            return 0.0
        return sum(profile.knowledge_points.values()) / len(profile.knowledge_points)
