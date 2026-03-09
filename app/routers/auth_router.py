
from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.user_schema import (
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services import auth_service
from app.utils.jwt_handler import get_current_user

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=dict,
    status_code=201,
    summary="Register a new user account",
)
def register(
    request: Request,
    payload: UserRegister,
    db: Session = Depends(get_db),
) -> dict:
    """
    Create a new student or researcher account.

    Returns the standard success envelope containing the newly created user.
    """
    user = auth_service.register_user(db=db, data=payload)
    return {
        "status": "success",
        "data": UserResponse.model_validate(user).model_dump(mode="json"),
    }


@router.post(
    "/login",
    response_model=dict,
    summary="Authenticate and receive JWT tokens",
)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> dict:
    """
    Authenticate with email and password.

    Returns an access token (24 h) and a refresh token (7 days).
    After 5 consecutive failures the account is locked for 15 minutes.
    """
    tokens = auth_service.login_user(db=db, data=payload)
    return {
        "status": "success",
        "data": TokenResponse(**tokens).model_dump(mode="json"),
    }


@router.get(
    "/me",
    response_model=dict,
    summary="Get the current authenticated user",
)
def me(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the profile of the currently authenticated user."""
    return {
        "status": "success",
        "data": UserResponse.model_validate(current_user).model_dump(mode="json"),
    }


@router.post(
    "/refresh",
    response_model=dict,
    summary="Refresh access token using a valid refresh token",
)
def refresh(
    request: Request,
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Exchange a valid refresh token for a new access token and refresh token pair.
    """
    tokens = auth_service.refresh_token(token=payload.refresh_token, db=db)
    return {
        "status": "success",
        "data": TokenResponse(**tokens).model_dump(mode="json"),
    }
