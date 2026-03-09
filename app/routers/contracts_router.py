
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.contract_schema import ContractListResponse, ContractResponse
from app.services import contract_service
from app.utils.jwt_handler import get_current_user, require_role

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=dict, summary="List own contracts")
def list_contracts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return all contracts for the authenticated user.

    Students see contracts where they are the student.
    Researchers see contracts where they are the researcher.
    Admins see all contracts.
    """
    contracts = contract_service.get_user_contracts(
        db=db,
        user_id=current_user.id,
        role=current_user.role,
    )
    response = ContractListResponse(
        items=[ContractResponse.model_validate(c) for c in contracts],
        total=len(contracts),
    )
    return {"status": "success", "data": response.model_dump()}


@router.get("/{contract_id}", response_model=dict, summary="Get contract details")
def get_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Fetch full details for a specific contract including job info and payment status.

    Access is restricted to the student, researcher involved, or an admin.
    """
    details = contract_service.get_contract_with_details(
        db=db,
        contract_id=contract_id,
    )

    is_participant = (
        str(current_user.id) in (details["student_id"], details["researcher_id"])
    )
    is_admin = current_user.role == "admin"

    if not is_participant and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a participant in this contract.",
        )

    return {"status": "success", "data": details}


@router.post(
    "/{contract_id}/start",
    response_model=dict,
    summary="Start work on a contract",
)
def start_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(require_role("researcher")),
    db: Session = Depends(get_db),
) -> dict:
    """
    Mark a contract as 'in_progress'.

    Only the researcher assigned to the contract may start it, and only after
    the student has escrowed the agreed payment.
    """
    contract = contract_service.start_contract(
        db=db,
        contract_id=contract_id,
        researcher_id=current_user.id,
    )
    return {
        "status": "success",
        "data": ContractResponse.model_validate(contract).model_dump(),
    }
