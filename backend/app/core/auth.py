import hashlib
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its SHA-256 hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(user_id: int, username: str) -> str:
    """Create a JWT access token for the given user."""
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET.get_secret_value(), algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Returns the payload dict."""
    settings = get_settings()
    return jwt.decode(
        token, settings.JWT_SECRET.get_secret_value(), algorithms=[JWT_ALGORITHM]
    )
