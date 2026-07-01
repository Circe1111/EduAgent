from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class TaskType(str, Enum):
    quiz = "quiz"
    lecture = "lecture"
    explanation = "explanation"
    path_planning = "path_planning"
    code_review = "code_review"


class IntentResult(BaseModel):
    task_type: TaskType = Field(..., description="Recognized task type")
    knowledge_points: List[str] = Field(
        default_factory=list, description="Identified knowledge points"
    )
    difficulty: float = Field(
        ..., ge=0.0, le=1.0, description="Estimated difficulty level (0-1)"
    )
    output_type: str = Field(..., description="Desired output format")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence in intent classification"
    )
