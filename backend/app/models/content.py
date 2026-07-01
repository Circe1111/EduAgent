from typing import Dict, List, Any
from pydantic import BaseModel, Field


class GeneratedContent(BaseModel):
    content: str = Field(..., description="Generated text content")
    content_type: str = Field(..., description="Type of content (e.g., quiz, explanation)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for the generation"
    )


class CritiqueResult(BaseModel):
    passed: bool = Field(..., description="Whether content passed quality checks")
    issues: List[str] = Field(default_factory=list, description="List of identified issues")
    issue_types: List[str] = Field(
        default_factory=list, description="Categories of issues"
    )
    fix_suggestions: List[str] = Field(
        default_factory=list, description="Suggested fixes for each issue"
    )
