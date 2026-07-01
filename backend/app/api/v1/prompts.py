import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.prompt_template import PromptTemplate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prompts"])


class PromptTemplateResponse(BaseModel):
    id: int
    code: str
    title: str
    role: str
    task: str
    template: str
    variables: str
    scenario: str
    created_at: str


class PromptTemplateListItem(BaseModel):
    id: int
    code: str
    title: str
    role: str
    task: str
    variables: str
    scenario: str
    created_at: str


@router.get("/prompt-templates", response_model=List[PromptTemplateListItem])
async def list_prompt_templates(
    db: AsyncSession = Depends(get_db),
):
    """Return all prompt templates sorted by code ascending."""
    try:
        result = await db.execute(
            select(PromptTemplate).order_by(PromptTemplate.code.asc())
        )
        templates = result.scalars().all()
        return [
            PromptTemplateListItem(
                id=t.id,
                code=t.code,
                title=t.title,
                role=t.role,
                task=t.task,
                variables=t.variables,
                scenario=t.scenario,
                created_at=str(t.created_at),
            )
            for t in templates
        ]
    except Exception as exc:
        logger.exception("Failed to list prompt templates")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompt templates: {str(exc)}",
        )


@router.get("/prompt-templates/{code}", response_model=PromptTemplateResponse)
async def get_prompt_template(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Return a single prompt template by its code (e.g. 'P001')."""
    try:
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.code == code)
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt template with code '{code}' not found",
            )
        return PromptTemplateResponse(
            id=template.id,
            code=template.code,
            title=template.title,
            role=template.role,
            task=template.task,
            template=template.template,
            variables=template.variables,
            scenario=template.scenario,
            created_at=str(template.created_at),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get prompt template")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt template: {str(exc)}",
        )
