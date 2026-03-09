
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.message import Notification
from app.models.submission import Revision, Submission, SubmissionFile
from app.models.user import User
from app.schemas.submission_schema import RevisionRequest, SubmissionCreate
from app.utils.security import sanitize_input


def _get_notification_target(db: Session, user_id: uuid.UUID) -> User:
    user: User | None = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return user


def _create_notification(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    message: str,
    notification_type: str,
) -> None:
    """Persist an in-app notification record for *user_id*."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(notification)


def create_submission(
    db: Session,
    contract_id: uuid.UUID,
    researcher_id: uuid.UUID,
    data: SubmissionCreate,
) -> Submission:
    """
    Create a new submission for *contract_id*.

    Preconditions:
    - Contract must exist.
    - The calling researcher must own the contract.
    - Contract status must be 'in_progress'.

    Side-effects:
    - Transitions contract status to 'submitted'.
    - Creates an in-app Notification for the student.

    Raises:
        HTTPException 404 — contract not found.
        HTTPException 403 — researcher does not own the contract.
        HTTPException 400 — contract is not in 'in_progress' status.
    """
    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == contract_id).first()
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    if contract.researcher_id != researcher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the researcher on this contract",
        )

    if contract.status not in ("in_progress", "revision_requested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot submit work for a contract with status '{contract.status}'. "
                "Contract must be 'in_progress' or 'revision_requested'."
            ),
        )

    notes = sanitize_input(data.submission_notes)

    submission = Submission(
        contract_id=contract_id,
        researcher_id=researcher_id,
        submission_notes=notes,
        status="submitted",
    )
    db.add(submission)

    contract.status = "submitted"

    _create_notification(
        db=db,
        user_id=contract.student_id,
        title="New submission ready for review",
        message=(
            "Your researcher has submitted work for contract "
            f"{contract_id}. Please review it."
        ),
        notification_type="submission_created",
    )

    db.commit()
    db.refresh(submission)
    return submission


def attach_submission_file(
    db: Session,
    submission_id: uuid.UUID,
    researcher_id: uuid.UUID,
    s3_key: str,
    file_name: str,
    file_size: int,
) -> SubmissionFile:
    """
    Attach an already-uploaded S3 file record to a submission.

    Preconditions:
    - Submission must exist.
    - The calling researcher must own the submission.

    Raises:
        HTTPException 404 — submission not found.
        HTTPException 403 — researcher does not own the submission.
    """
    submission: Submission | None = (
        db.query(Submission).filter(Submission.id == submission_id).first()
    )
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found",
        )

    if submission.researcher_id != researcher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this submission",
        )

    sub_file = SubmissionFile(
        submission_id=submission_id,
        file_name=file_name,
        file_url=s3_key,
        file_size=file_size,
    )
    db.add(sub_file)
    db.commit()
    db.refresh(sub_file)
    return sub_file


def get_submission(db: Session, submission_id: uuid.UUID) -> Submission:
    """
    Fetch a single submission by primary key.

    Raises:
        HTTPException 404 — if not found.
    """
    submission: Submission | None = (
        db.query(Submission).filter(Submission.id == submission_id).first()
    )
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found",
        )
    return submission


def get_contract_submissions(
    db: Session,
    contract_id: uuid.UUID,
) -> list[Submission]:
    """Return all submissions for a given contract, ordered newest first."""
    return (
        db.query(Submission)
        .filter(Submission.contract_id == contract_id)
        .order_by(Submission.created_at.desc())
        .all()
    )


def request_revision(
    db: Session,
    submission_id: uuid.UUID,
    student_id: uuid.UUID,
    data: RevisionRequest,
) -> Revision:
    """
    Request a revision for a submission.

    Preconditions:
    - Submission must exist.
    - The calling student must own the contract associated with the submission.
    - Submission status must be 'submitted'.

    Side-effects:
    - Sets submission status to 'revision_requested'.
    - Transitions contract status to 'revision_requested'.
    - Creates a Revision record.
    - Notifies the researcher.

    Raises:
        HTTPException 404 — submission not found.
        HTTPException 403 — student does not own the contract.
        HTTPException 400 — submission is not in 'submitted' status.
    """
    submission = get_submission(db, submission_id)

    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == submission.contract_id).first()
    )
    if contract is None or contract.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own the contract associated with this submission",
        )

    if submission.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot request a revision for a submission with status "
                f"'{submission.status}'. Submission must be 'submitted'."
            ),
        )

    message_text = sanitize_input(data.message)

    submission.status = "revision_requested"
    contract.status = "revision_requested"

    revision = Revision(
        submission_id=submission_id,
        requested_by=student_id,
        message=message_text,
    )
    db.add(revision)

    _create_notification(
        db=db,
        user_id=contract.researcher_id,
        title="Revision requested",
        message=(
            f"The student has requested a revision for submission {submission_id}. "
            f"Reason: {message_text}"
        ),
        notification_type="revision_requested",
    )

    db.commit()
    db.refresh(revision)
    return revision


def approve_submission(
    db: Session,
    submission_id: uuid.UUID,
    student_id: uuid.UUID,
) -> Submission:
    """
    Approve a submission and mark the contract as completed.

    Preconditions:
    - Submission must exist.
    - The calling student must own the contract.
    - Submission status must be 'submitted'.

    Side-effects:
    - Sets submission status to 'approved'.
    - Transitions contract status to 'completed'.
    - Payment release is handled separately by the student via the payments endpoint.

    Raises:
        HTTPException 404 — submission not found.
        HTTPException 403 — student does not own the contract.
        HTTPException 400 — submission is not in 'submitted' status.
    """
    submission = get_submission(db, submission_id)

    contract: Contract | None = (
        db.query(Contract).filter(Contract.id == submission.contract_id).first()
    )
    if contract is None or contract.student_id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own the contract associated with this submission",
        )

    if submission.status not in ("submitted", "revision_requested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot approve a submission with status '{submission.status}'. "
                "Submission must be 'submitted'."
            ),
        )

    submission.status = "approved"
    contract.status = "completed"

    db.commit()
    db.refresh(submission)
    return submission
