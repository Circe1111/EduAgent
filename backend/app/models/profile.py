from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    knowledge_points: Dict[str, float] = Field(
        default_factory=dict,
        description="Skill name mapped to mastery level (0.0 - 1.0)",
    )
    overall_difficulty: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Overall difficulty preference"
    )
    learning_style: str = Field(
        default="adaptive", description="Preferred learning style"
    )
    session_count: int = Field(default=0, description="Number of completed sessions")
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last profile update timestamp"
    )
