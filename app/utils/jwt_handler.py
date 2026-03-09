
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_db

settings = get_settings()
_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Token creation helpers
# ---------------------------------------------------------------------------

def _build_payload(data: dict[str, Any], expires_delta: timedelta) -> dict[str, Any]:
    payload = data.copy()
    now = datetime.now(timezone.utc)
    payload["exp"] = now + expires_delta
    payload["iat"] = now
    payload["jti"] = str(uuid.uuid4())   # unique ID so same-second tokens always differ
    return payload


def create_access_token(user_id: str, role: str) -> str:
    """Create a signed JWT access token valid for ``JWT_EXPIRE_HOURS`` hours."""
    expires = timedelta(hours=settings.jwt_expire_hours)
    payload = _build_payload(
        {"sub": user_id, "role": role, "type": "access"},
        expires,
    )
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """Create a signed JWT refresh token valid for ``REFRESH_TOKEN_EXPIRE_DAYS`` days."""
    expires = timedelta(days=settings.refresh_token_expire_days)
    payload = _build_payload(
        {"sub": user_id, "type": "refresh"},
        expires,
    )
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------

def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException 401 — if the token is expired, malformed, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Any:
    """
    FastAPI dependency that extracts and validates the Bearer token, then
    fetches and returns the authenticated User from the database.

    Raises:
        HTTPException 401 — if the token is missing, invalid, or the user
        does not exist or is suspended/deleted.
    """
    # Lazy import to avoid circular dependency at module load time
    from app.models.user import User  # noqa: PLC0415

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    user_id: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")

    if user_id is None or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status in ("suspended", "deleted"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is suspended or deleted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*roles: str):
    """
    Dependency factory that restricts an endpoint to users whose role is one
    of the provided *roles*.

    Usage::

        @router.get("/admin-only")
        def admin_view(user = Depends(require_role("admin"))):
            ...
    """

    def _check_role(current_user: Any = Depends(get_current_user)) -> Any:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): {', '.join(roles)}. "
                    f"Your role: {current_user.role}"
                ),
            )
        return current_user

    return _check_role
