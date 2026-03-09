
import logging
import uuid

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import ResearcherProfile, StudentProfile, User
from app.schemas.account_schema import (
    ContactUpdateRequest,
    LocationUpdateRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    ResearcherProfileUpdateRequest,
    StudentProfileUpdateRequest,
)

logger = logging.getLogger(__name__)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_account(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id, User.status != "deleted").first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def update_profile(db: Session, user_id: uuid.UUID, data: ProfileUpdateRequest) -> User:
    user = get_account(db, user_id)
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    logger.info("Profile updated: user=%s fields=%s", user_id, list(updates.keys()))
    return user


def update_contact(db: Session, user_id: uuid.UUID, data: ContactUpdateRequest) -> User:
    user = get_account(db, user_id)
    if data.email and data.email != user.email:
        clash = db.query(User).filter(User.email == data.email, User.id != user_id).first()
        if clash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = data.email
        user.is_verified = False  # require re-verification
    if data.phone is not None:
        user.phone = data.phone
    if data.whatsapp_number is not None:
        user.whatsapp_number = data.whatsapp_number
    db.commit()
    db.refresh(user)
    return user


def update_location(db: Session, user_id: uuid.UUID, data: LocationUpdateRequest) -> User:
    """Update student-profile location fields (country) or user-level timezone/city."""
    user = get_account(db, user_id)
    # For students: persist country on StudentProfile
    if user.role == "student" and user.student_profile and data.country is not None:
        user.student_profile.country = data.country
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user_id: uuid.UUID, data: PasswordChangeRequest) -> None:
    user = get_account(db, user_id)
    if not _pwd_context.verify(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.password_hash = _pwd_context.hash(data.new_password)
    db.commit()
    logger.info("Password changed: user=%s", user_id)


def update_student_profile(
    db: Session,
    user_id: uuid.UUID,
    data: StudentProfileUpdateRequest,
) -> StudentProfile:
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if profile is None:
        profile = StudentProfile(user_id=user_id)
        db.add(profile)
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def update_researcher_profile(
    db: Session,
    user_id: uuid.UUID,
    data: ResearcherProfileUpdateRequest,
) -> ResearcherProfile:
    profile = db.query(ResearcherProfile).filter(ResearcherProfile.user_id == user_id).first()
    if profile is None:
        profile = ResearcherProfile(user_id=user_id)
        db.add(profile)
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
