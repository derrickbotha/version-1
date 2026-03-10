from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.assignment import Assignment, AssignmentStatus
from ..services.assignment_service import update_pipeline_log

router = APIRouter(prefix="/webhook", tags=["internal"])

N8N_SECRET = "n8n-internal-secret-changeme"

def verify_n8n(x_n8n_secret: str = Header(...)):
    if x_n8n_secret != N8N_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

@router.post("/n8n/status")
def update_status(body: dict, db: Session = Depends(get_db), _=Depends(verify_n8n)):
    assignment_id = body.get("assignment_id")
    stage = body.get("stage")
    status = body.get("status")
    result = body.get("result", {})

    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")

    update_pipeline_log(db, assignment_id, stage, result)

    status_map = {
        "researching":  AssignmentStatus.researching,
        "writing":      AssignmentStatus.writing,
        "qa_check":     AssignmentStatus.qa_check,
        "prof_review":  AssignmentStatus.prof_review,
        "completed":    AssignmentStatus.completed,
        "failed":       AssignmentStatus.failed,
    }
    if status in status_map:
        a.status = status_map[status]

    if status == "completed" and result.get("docx_path"):
        a.docx_path = result["docx_path"]
        a.plagiarism_score = result.get("plagiarism_score")
        a.quality_score = result.get("quality_score")

    db.commit()
    return {"ok": True}
