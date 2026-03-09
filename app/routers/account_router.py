
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.account_schema import (
    AccountResponse,
    ContactUpdateRequest,
    LocationUpdateRequest,
    PasswordChangeRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    ResearcherProfileResponse,
    ResearcherProfileUpdateRequest,
    StudentProfileResponse,
    StudentProfileUpdateRequest,
)
from app.services import account_service
from app.utils.jwt_handler import get_current_user

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("", response_model=dict, summary="Get full account details")
def get_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = account_service.get_account(db, current_user.id)
    profile = ProfileResponse.model_validate(user)
    student = (
        StudentProfileResponse.model_validate(user.student_profile)
        if user.student_profile else None
    )
    researcher = (
        ResearcherProfileResponse.model_validate(user.researcher_profile)
        if user.researcher_profile else None
    )
    return {
        "status": "success",
        "data": AccountResponse(
            profile=profile,
            student_profile=student,
            researcher_profile=researcher,
        ).model_dump(),
    }


@router.patch("/profile", response_model=dict, summary="Update name / phone / WhatsApp")
def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = account_service.update_profile(db, current_user.id, body)
    return {"status": "success", "data": ProfileResponse.model_validate(user).model_dump()}


@router.patch("/contact", response_model=dict, summary="Update email / phone")
def update_contact(
    body: ContactUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = account_service.update_contact(db, current_user.id, body)
    return {"status": "success", "data": ProfileResponse.model_validate(user).model_dump()}


@router.patch("/location", response_model=dict, summary="Update location info")
def update_location(
    body: LocationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = account_service.update_location(db, current_user.id, body)
    return {"status": "success", "data": ProfileResponse.model_validate(user).model_dump()}


@router.post("/security/change-password", response_model=dict, summary="Change password")
def change_password(
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    account_service.change_password(db, current_user.id, body)
    return {"status": "success", "data": {"message": "Password updated successfully"}}


@router.patch("/student-profile", response_model=dict, summary="Update student profile")
def update_student_profile(
    body: StudentProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = account_service.update_student_profile(db, current_user.id, body)
    return {"status": "success", "data": StudentProfileResponse.model_validate(profile).model_dump()}


@router.patch("/researcher-profile", response_model=dict, summary="Update researcher profile")
def update_researcher_profile(
    body: ResearcherProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    profile = account_service.update_researcher_profile(db, current_user.id, body)
    return {"status": "success", "data": ResearcherProfileResponse.model_validate(profile).model_dump()}
