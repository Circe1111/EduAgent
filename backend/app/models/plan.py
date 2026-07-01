from typing import List
from pydantic import BaseModel, Field


class PathNode(BaseModel):
    knowledge_point: str = Field(..., description="Target knowledge point")
    order: int = Field(..., description="Sequence order in the path")
    resources: List[str] = Field(
        default_factory=list, description="Recommended resource IDs/URLs"
    )
    estimated_time: str = Field(
        ..., description="Estimated time to complete (e.g., '30m', '2h')"
    )
    prerequisites: List[str] = Field(
        default_factory=list, description="Prerequisite knowledge points"
    )


class LearningPath(BaseModel):
    nodes: List[PathNode] = Field(
        default_factory=list, description="Ordered learning nodes"
    )
    total_estimated_time: str = Field(
        ..., description="Total estimated time for the full path"
    )
