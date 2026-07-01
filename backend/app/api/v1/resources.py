import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models.session import Session as SessionDB

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/resources/{resource_id}")
async def get_resource(
    resource_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve a stored resource by its identifier.
    """
    try:
        # Resource IDs are expected to be in the form {session_id}_{index}
        if "_" in resource_id:
            session_id, idx_str = resource_id.rsplit("_", 1)
            try:
                idx = int(idx_str)
            except ValueError:
                idx = None
        else:
            session_id = resource_id
            idx = None

        result = await db.execute(
            select(SessionDB).where(SessionDB.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found",
            )

        messages = session.messages or []
        if idx is not None and 0 <= idx < len(messages):
            msg = messages[idx]
            return {
                "resource_id": resource_id,
                "content": msg.get("content", ""),
                "metadata": msg.get("metadata", {}),
            }

        # Fallback: return first assistant message
        for msg in messages:
            if msg.get("role") == "assistant":
                return {
                    "resource_id": resource_id,
                    "content": msg.get("content", ""),
                    "metadata": msg.get("metadata", {}),
                }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve resource")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve resource: {str(exc)}",
        )


@router.get("/resources")
async def list_resources(
    session_id: str = Query(..., description="Session identifier"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    List resources associated with a given session.
    """
    try:
        result = await db.execute(
            select(SessionDB).where(SessionDB.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        resources = []
        messages = session.messages or []
        for idx, msg in enumerate(messages):
            if msg.get("role") == "assistant":
                resources.append(
                    {
                        "resource_id": f"{session_id}_{idx}",
                        "content": msg.get("content", ""),
                        "metadata": msg.get("metadata", {}),
                    }
                )

        return resources
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list resources")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list resources: {str(exc)}",
        )
