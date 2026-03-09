
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.payment import Wallet
from app.models.user import ResearcherProfile, StudentProfile, User
from app.schemas.user_schema import UserLogin, UserRegister
from app.utils.jwt_handler import create_access_token, create_refresh_token, decode_token
from app.utils.security import hash_password, verify_password

_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15


def register_user(db: Session, data: UserRegister) -> User:
    """
    Register a new user.

    Steps:
    1. Verify the email address is not already in use.
    2. Hash the password.
    3. Create the User row.
    4. Create the matching profile row (StudentProfile or ResearcherProfile).
    5. Create an empty Wallet for the user.
    6. Commit and return the persisted User.

    Raises:
        HTTPException 409 — email already registered.
    """
    existing: User | None = db.query(User).filter(User.email == data.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists",
        )

    new_user = User(
        id=uuid.uuid4(),
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        role=data.role,
        phone=data.phone,
        status="active",
        is_verified=False,
        failed_login_attempts=0,
    )
    db.add(new_user)
    db.flush()  # obtain new_user.id before creating related rows

    # Create role-specific profile
    if data.role == "student":
        profile = StudentProfile(id=uuid.uuid4(), user_id=new_user.id)
        db.add(profile)
    elif data.role == "researcher":
        profile = ResearcherProfile(
            id=uuid.uuid4(),
            user_id=new_user.id,
            expertise=[],
        )
        db.add(profile)

    # Create empty wallet
    wallet = Wallet(user_id=new_user.id, balance=0)
    db.add(wallet)

    db.commit()
    db.refresh(new_user)
    return new_user


def login_user(db: Session, data: UserLogin) -> dict[str, str]:
    """
    Authenticate a user and return JWT tokens.

    Account lockout policy: after ``_MAX_FAILED_ATTEMPTS`` consecutive failures
    the account is locked for ``_LOCKOUT_MINUTES`` minutes.

    Returns:
        dict with keys ``access_token``, ``refresh_token``, ``token_type``.

    Raises:
        HTTPException 401 — invalid credentials or account locked/suspended.
    """
    user: User | None = (
        db.query(User).filter(User.email == data.email, User.status != "deleted").first()
    )

    _invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        raise _invalid_exc

    if user.status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is suspended. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check lockout
    now = datetime.now(timezone.utc)
    if user.locked_until is not None:
        locked_until_aware = (
            user.locked_until
            if user.locked_until.tzinfo is not None
            else user.locked_until.replace(tzinfo=timezone.utc)
        )
        if locked_until_aware > now:
            remaining = int((locked_until_aware - now).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    f"Account is temporarily locked due to too many failed login attempts. "
                    f"Try again in {remaining} minute(s)."
                ),
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            # Lockout period expired — clear it
            user.failed_login_attempts = 0
            user.locked_until = None

    if not verify_password(data.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= _MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=_LOCKOUT_MINUTES)
        db.commit()
        raise _invalid_exc

    # Successful login — reset counters
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    access_token = create_access_token(user_id=str(user.id), role=user.role)
    refresh_token = create_refresh_token(user_id=str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_token(token: str, db: Session) -> dict[str, str]:
    """
    Validate a refresh token and issue a new access token.

    Returns:
        dict with keys ``access_token``, ``refresh_token``, ``token_type``.

    Raises:
        HTTPException 401 — token is invalid, expired, or not a refresh token.
    """
    from app.models.user import User  # noqa: PLC0415 — local import avoids circular ref

    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: a refresh token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None or user.status in ("suspended", "deleted"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_access_token(user_id=str(user.id), role=user.role)
    new_refresh_token = create_refresh_token(user_id=str(user.id))

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
