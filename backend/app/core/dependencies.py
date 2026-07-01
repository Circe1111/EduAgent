from typing import Optional
from fastapi import Header, HTTPException, status


async def get_current_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id")
) -> str:
    """
    Extract session ID from request header.
    If missing, generate a new one (for anonymous sessions).
    """
    if x_session_id is None:
        import uuid
        return str(uuid.uuid4())
    return x_session_id
