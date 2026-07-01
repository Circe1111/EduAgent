from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.core.database import async_engine, Base, create_redis_pool, close_redis_pool
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.api.v1 import router as api_v1_router
from app.api.v1.auth import router as auth_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.
    Handles startup (DB init, Redis, Qdrant) and shutdown cleanup.
    """
    # Startup
    setup_logging(settings.LOG_LEVEL)
    setup_telemetry()

    # Initialize database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize Redis
    create_redis_pool()

    # Initialize Qdrant client (stored on app state)
    app.state.qdrant = AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    yield

    # Shutdown
    await close_redis_pool()
    await async_engine.dispose()
    if hasattr(app.state, "qdrant"):
        await app.state.qdrant.close()


app = FastAPI(
    title="EduAgent 2.0 API",
    description="AI-Powered Adaptive Learning Backend",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Resource not found", "path": str(request.url)},
    )


@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors() if hasattr(exc, "errors") else []},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# Include routers
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
