import os

import jwt
from fastapi import Depends, Header, HTTPException

_JWT_ALGORITHMS = ["HS256"]
_AUDIENCE = "authenticated"


def is_auth_enabled() -> bool:
    return bool(os.getenv("SUPABASE_JWT_SECRET", "").strip())


def verify_token(token: str) -> str:
    """Validate a Supabase JWT (HS256) and return the user id (sub)."""
    secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "Authentication is not configured")
    try:
        payload = jwt.decode(token, secret, algorithms=_JWT_ALGORITHMS, audience=_AUDIENCE)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(401, "Invalid token audience")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or malformed token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token has no subject")
    return user_id


def require_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: reject requests without a valid Bearer token."""
    if not is_auth_enabled():
        raise HTTPException(503, "Authentication is not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    return verify_token(authorization.split(" ", 1)[1].strip())


def optional_user(authorization: str | None = Header(default=None)) -> str | None:
    """FastAPI dependency: return the user id if a valid token is provided, else None."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return verify_token(authorization.split(" ", 1)[1].strip())
    except HTTPException:
        return None