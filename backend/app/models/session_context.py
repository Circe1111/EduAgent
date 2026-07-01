from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.content import CritiqueResult, GeneratedContent
from app.models.intent import IntentResult
from app.models.plan import LearningPath
from app.models.profile import StudentProfile


class SessionContext(BaseModel):
    session_id: str
    user_id: str
    task_intent: Optional[IntentResult] = None
    student_profile: Optional[StudentProfile] = None
    knowledge_points: List[str] = Field(default_factory=list)
    difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    retrieval_results: List[dict] = Field(default_factory=list)
    history_summary: Optional[str] = None
    task_spec: Optional[dict] = None
    generated_content: Optional[GeneratedContent] = None
    critique_result: Optional[CritiqueResult] = None
    learning_plan: Optional[LearningPath] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    def add_error(self, error: str) -> "SessionContext":
        self.errors.append(error)
        return self

    def is_valid(self) -> bool:
        return len(self.errors) == 0 and bool(self.session_id) and bool(self.user_id)
