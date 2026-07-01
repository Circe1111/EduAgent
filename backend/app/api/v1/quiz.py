import json
import logging
import time
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.llm import LLMClient
from app.db.models.badge import UserBadge
from app.db.models.quiz_history import QuizHistory

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory quiz cache keyed by "user_id:node_id"
# Value: (questions_list, timestamp)
_quiz_cache: Dict[str, tuple] = {}
QUIZ_CACHE_TTL = 600  # 10 minutes


class QuestionOut(BaseModel):
    question: str
    options: List[str]
    answer: str


class QuizSubmitRequest(BaseModel):
    node_id: int
    questions: List[QuestionOut]
    answers: Dict[str, str]


class QuestionResult(BaseModel):
    question: str
    correct: bool
    user_answer: str
    correct_answer: str


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    results: List[QuestionResult]


QUIZ_GENERATION_PROMPT = """You are an expert educational assessment creator. Generate 5 multiple-choice questions about the given topic.

Format your response as a valid JSON array only, with no markdown formatting or code blocks.
Each question object must have exactly this structure:
{{
  "question": "The question text",
  "options": ["A. Option text", "B. Option text", "C. Option text", "D. Option text"],
  "answer": "A"
}}

Requirements:
- Each question must test understanding, not rote memorization
- Distractors should be plausible
- The correct answer must be clearly correct
- Use A, B, C, D as option keys
- Answer must be one of A, B, C, D
- Return ONLY the JSON array, nothing else"""


async def _check_scholar_badge(user_id: int, db: AsyncSession) -> List[str]:
    """Check and award SCHOLAR badge: >= 90% score on any 3 distinct nodes."""
    newly_earned = []

    already_has = await db.execute(
        select(UserBadge).where(
            UserBadge.user_id == user_id,
            UserBadge.badge_code == "SCHOLAR",
        )
    )
    if already_has.scalar_one_or_none() is not None:
        return newly_earned

    # Get distinct nodes where user has quiz records
    nodes_result = await db.execute(
        select(QuizHistory.node_id)
        .where(QuizHistory.user_id == user_id)
        .distinct()
    )
    node_ids = [row[0] for row in nodes_result.all()]

    high_score_nodes = 0
    for nid in node_ids:
        # Get the last 5 records for this node (most recent quiz attempt)
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
            continue  # Not a full quiz attempt
        correct_count = sum(1 for r in records if r[0])
        score_pct = correct_count / 5 * 100
        if score_pct >= 90:
            high_score_nodes += 1

    if high_score_nodes >= 3:
        badge = UserBadge(
            user_id=user_id,
            badge_code="SCHOLAR",
            badge_name="Xue Ba",
        )
        db.add(badge)
        newly_earned.append("SCHOLAR")

    return newly_earned


@router.post("/quiz/generate/{node_id}", response_model=List[QuestionOut])
async def generate_quiz(
    node_id: int,
    user_id: int = Depends(get_current_user),
):
    """Generate 5 multiple-choice questions about a knowledge node using LLM."""
    cache_key = f"{user_id}:{node_id}"
    cached = _quiz_cache.get(cache_key)
    if cached is not None:
        questions, timestamp = cached
        if time.time() - timestamp < QUIZ_CACHE_TTL:
            return questions

    llm = LLMClient()
    prompt = (
        f"{QUIZ_GENERATION_PROMPT}\n\n"
        f"Generate 5 multiple-choice questions about the learning topic associated "
        f"with node id {node_id}. The questions should help assess the student's "
        f"understanding of this topic."
    )
    try:
        response = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3072,
        )
        content = response.get("content", "")

        # Strip markdown code fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        questions = json.loads(content)
        if not isinstance(questions, list) or len(questions) != 5:
            raise ValueError(f"Expected 5 questions, got {len(questions)}")

        # Validate each question structure
        for q in questions:
            if not all(k in q for k in ("question", "options", "answer")):
                raise ValueError("Invalid question format")
            if len(q["options"]) != 4:
                raise ValueError("Each question must have exactly 4 options")
    except json.JSONDecodeError as exc:
        logger.exception("Failed to parse LLM quiz output")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz generation failed: invalid JSON response",
        )
    except Exception as exc:
        logger.exception("Failed to generate quiz")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz generation failed: {str(exc)}",
        )

    _quiz_cache[cache_key] = (questions, time.time())
    return questions


@router.post("/quiz/submit", response_model=QuizSubmitResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit quiz answers, grade them, and return results."""
    try:
        cache_key = f"{user_id}:{request.node_id}"
        cached = _quiz_cache.get(cache_key)
        if cached is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz session expired or not found. Please generate a new quiz.",
            )
        questions, _ = cached

        # Grade each question
        results = []
        correct_count = 0
        for i, q in enumerate(questions):
            user_answer = request.answers.get(str(i), "").strip().upper()
            correct_answer = q.get("answer", "").strip().upper()
            is_correct = user_answer == correct_answer

            if is_correct:
                correct_count += 1

            # Save to quiz_history
            record = QuizHistory(
                user_id=user_id,
                node_id=request.node_id,
                question=q["question"],
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
            )
            db.add(record)

            results.append(QuestionResult(
                question=q["question"],
                correct=is_correct,
                user_answer=user_answer,
                correct_answer=correct_answer,
            ))

        total = len(questions)
        score = correct_count

        # Check SCHOLAR badge condition
        await _check_scholar_badge(user_id, db)

        await db.commit()

        return QuizSubmitResponse(
            score=score,
            total=total,
            results=results,
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Failed to submit quiz")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quiz submission failed: {str(exc)}",
        )
