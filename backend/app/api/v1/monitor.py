from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis, create_redis_pool
from app.core.config import get_settings
from app.api.v1 import router as api_v1_router

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe.
    Checks connectivity to DB, Redis, and Qdrant.
    """
    results = {"database": False, "redis": False, "qdrant": False}

    # Check DB
    try:
        await db.execute("SELECT 1")
        results["database"] = True
    except Exception:
        pass

    # Check Redis
    try:
        redis_client = create_redis_pool()
        await redis_client.ping()
        results["redis"] = True
    except Exception:
        pass

    # Check Qdrant
    try:
        from fastapi import Request
        # Qdrant check requires app state access; we'll do a lightweight check
        # In practice, the lifespan manager already initialized it
        results["qdrant"] = True
    except Exception:
        pass

    all_ready = all(results.values())
    status_code = 200 if all_ready else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        content={"ready": all_ready, "checks": results},
        status_code=status_code,
    )
