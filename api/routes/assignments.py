from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.assignment import AssignmentCreate, AssignmentOut, AssignmentStatusOut
from ..services.auth_service import get_current_user
from ..services.assignment_service import (
    create_assignment, get_user_assignments, get_assignment, trigger_n8n_pipeline,
)
from ..models.assignment import AssignmentStatus
import os

router = APIRouter(prefix="/assignments", tags=["assignments"])

def current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    try:
        return get_current_user(token, db)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("", response_model=AssignmentOut, status_code=201)
def create(body: AssignmentCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    data = body.dict()
    assignment = create_assignment(db, str(user.id), data)
    # Trigger n8n pipeline asynchronously
    exec_id = trigger_n8n_pipeline(assignment)
    assignment.n8n_execution_id = exec_id
    assignment.status = AssignmentStatus.researching
    db.commit()
    db.refresh(assignment)
    return assignment

@router.get("", response_model=List[AssignmentOut])
def list_assignments(user=Depends(current_user), db: Session = Depends(get_db)):
    return get_user_assignments(db, str(user.id))

@router.get("/{assignment_id}", response_model=AssignmentOut)
def get_one(assignment_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    try:
        return get_assignment(db, assignment_id, str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{assignment_id}/status", response_model=AssignmentStatusOut)
def get_status(assignment_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    try:
        a = get_assignment(db, assignment_id, str(user.id))
        return a
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{assignment_id}/download")
def download_docx(assignment_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    try:
        a = get_assignment(db, assignment_id, str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not a.docx_path or not os.path.exists(a.docx_path):
        raise HTTPException(status_code=404, detail="Document not ready yet")
    return FileResponse(
        path=a.docx_path,
        filename=os.path.basename(a.docx_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
