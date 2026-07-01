from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.database import get_db
from app.db.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response schemas ───────────────────────────────────────────────


class RegisterRequest(BaseModel):
    username: str
    password: str
    phone: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserInfo(BaseModel):
    id: int
    username: str
    phone: str | None = None
    daily_goal: int
    total_xp: int
    created_at: str


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with username and password."""
    # Check for existing username
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user = User(
        username=body.username,
        phone=body.phone or "",
        password_hash=hash_password(body.password),
        daily_goal=30,
        total_xp=0,
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(user.id, user.username)

    return AuthResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Log in with username and password. Returns a JWT token."""
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    access_token = create_access_token(user.id, user.username)

    return AuthResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user's profile."""
    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserInfo(
        id=user.id,
        username=user.username,
        phone=user.phone,
        daily_goal=user.daily_goal,
        total_xp=user.total_xp,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )
