from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas.user import UserCreate, UserLogin, UserOut, Token, TokenRefresh
from ..services.auth_service import (
    register_user, authenticate_user, create_access_token,
    create_refresh_token, decode_token, get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

def get_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization[7:]

@router.post("/register", response_model=UserOut, status_code=201)
def register(body: UserCreate, db: Session = Depends(get_db)):
    try:
        user = register_user(db, body.email, body.password, body.full_name,
                              body.academic_level, body.institution)
        return user
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/login", response_model=Token)
def login(body: UserLogin, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
    )

@router.post("/refresh", response_model=Token)
def refresh(body: TokenRefresh, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return Token(
        access_token=create_access_token({"sub": user_id}),
        refresh_token=create_refresh_token({"sub": user_id}),
    )

@router.get("/me", response_model=UserOut)
def me(token: str = Depends(get_token), db: Session = Depends(get_db)):
    try:
        user = get_current_user(token, db)
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
