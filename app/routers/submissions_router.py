
import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.submission_schema import RevisionRequest, SubmissionCreate
from app.services import submission_service
from app.utils import file_storage
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(tags=["Submissions"])


def _serialize_submission(submission, db: Session) -> dict:
    """Return a JSON-serialisable dict for a Submission ORM instance."""
    signed_urls = [
        file_storage.generate_signed_url(f.file_url)
        for f in submission.files
    ]
    return {
        "id": str(submission.id),
        "contract_id": str(submission.contract_id),
        "researcher_id": str(submission.researcher_id),
        "submission_notes": submission.submission_notes,
        "status": submission.status,
        "submitted_at": submission.created_at.isoformat(),
        "files": signed_urls,
    }


@router.post(
    "/submissions",
    response_model=dict,
    status_code=201,
    summary="Create a submission for a contract",
)
def create_submission(
    data: SubmissionCreate,
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Create a new submission for the given contract.

    Accessible by researchers only.  The researcher must own the contract and
    the contract must currently be in 'in_progress' status.
    """
    submission = submission_service.create_submission(
        db=db,
        contract_id=data.contract_id,
        researcher_id=current_user.id,
        data=data,
    )
    return {"status": "success", "data": _serialize_submission(submission, db)}


@router.post(
    "/submissions/{submission_id}/upload",
    response_model=dict,
    status_code=201,
    summary="Upload a file to a submission",
)
async def upload_submission_file(
    submission_id: uuid.UUID,
    file: UploadFile,
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Upload a file and attach it to the specified submission.

    Accessible by researchers only.  Validates extension, MIME type, and size
    before uploading to S3, then records the file metadata in the database.
    """
    file_content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    file_size = len(file_content)
    filename = file.filename or "upload"

    file_storage.validate_file(
        filename=filename,
        content_type=content_type,
        size=file_size,
    )

    s3_key = file_storage.upload_file(
        file_content=file_content,
        filename=filename,
        content_type=content_type,
        folder=f"submissions/{submission_id}",
    )

    sub_file = submission_service.attach_submission_file(
        db=db,
        submission_id=submission_id,
        researcher_id=current_user.id,
        s3_key=s3_key,
        file_name=filename,
        file_size=file_size,
    )

    signed_url = file_storage.generate_signed_url(sub_file.file_url)

    return {
        "status": "success",
        "data": {
            "id": str(sub_file.id),
            "submission_id": str(sub_file.submission_id),
            "file_name": sub_file.file_name,
            "file_size": sub_file.file_size,
            "url": signed_url,
        },
    }


@router.get(
    "/submissions/{submission_id}",
    response_model=dict,
    summary="Get a submission with signed file URLs",
)
def get_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Retrieve a submission and generate signed download URLs for all attached files.

    Accessible by any authenticated user who is a participant (student or
    researcher) on the underlying contract, or by admins.
    """
    from fastapi import HTTPException, status  # noqa: PLC0415

    submission = submission_service.get_submission(db, submission_id)

    # Authorisation: participant or admin
    from app.models.contract import Contract  # noqa: PLC0415

    contract = db.query(Contract).filter(Contract.id == submission.contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated contract not found",
        )

    is_participant = current_user.id in (contract.student_id, contract.researcher_id)
    if not is_participant and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a participant in this contract.",
        )

    return {"status": "success", "data": _serialize_submission(submission, db)}


@router.get(
    "/contracts/{contract_id}/submissions",
    response_model=dict,
    summary="List all submissions for a contract",
)
def list_contract_submissions(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    List all submissions for a contract.

    Accessible by any authenticated participant on the contract, or admins.
    """
    from fastapi import HTTPException, status  # noqa: PLC0415
    from app.models.contract import Contract  # noqa: PLC0415

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    is_participant = current_user.id in (contract.student_id, contract.researcher_id)
    if not is_participant and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a participant in this contract.",
        )

    submissions = submission_service.get_contract_submissions(db, contract_id)
    return {
        "status": "success",
        "data": {
            "items": [_serialize_submission(s, db) for s in submissions],
            "total": len(submissions),
        },
    }


@router.post(
    "/submissions/{submission_id}/revision",
    response_model=dict,
    status_code=201,
    summary="Request a revision on a submission",
)
def request_revision(
    submission_id: uuid.UUID,
    data: RevisionRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Request a revision for a submitted piece of work.

    Accessible by students only.  The student must own the contract associated
    with the submission and the submission must be in 'submitted' status.
    """
    revision = submission_service.request_revision(
        db=db,
        submission_id=submission_id,
        student_id=current_user.id,
        data=data,
    )
    return {
        "status": "success",
        "data": {
            "id": str(revision.id),
            "submission_id": str(revision.submission_id),
            "requested_by": str(revision.requested_by),
            "message": revision.message,
            "created_at": revision.created_at.isoformat(),
        },
    }


@router.post(
    "/submissions/{submission_id}/approve",
    response_model=dict,
    summary="Approve a submission",
)
def approve_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Approve a submitted piece of work and mark the contract as completed.

    Accessible by students only.  Payment release must be handled separately
    via the payments endpoint.
    """
    submission = submission_service.approve_submission(
        db=db,
        submission_id=submission_id,
        student_id=current_user.id,
    )
    return {"status": "success", "data": _serialize_submission(submission, db)}
