"""Password hashing and JWT helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str = "user") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": "nexamind",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer="nexamind",
        options={"require": ["exp", "sub"]},
    )
