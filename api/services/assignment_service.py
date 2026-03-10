import httpx
import json
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from ..models.assignment import Assignment, DeliveryMethod, ReviewType, AssignmentStatus
from ..models.billing import Order, OrderStatus
from ..config import settings
import uuid

# Generate or load encryption key (in production: load from env)
_FERNET_KEY = Fernet.generate_key()
_fernet = Fernet(_FERNET_KEY)

def encrypt(text: str) -> str:
    return _fernet.encrypt(text.encode()).decode()

def decrypt(text: str) -> str:
    return _fernet.decrypt(text.encode()).decode()

def create_assignment(db: Session, user_id: str, data: dict) -> Assignment:
    lms_pw = data.pop("lms_password", None)
    assignment = Assignment(
        user_id=user_id,
        lms_password_enc=encrypt(lms_pw) if lms_pw else None,
        **data,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

def get_user_assignments(db: Session, user_id: str) -> list:
    return db.query(Assignment).filter(Assignment.user_id == user_id).order_by(
        Assignment.created_at.desc()
    ).all()

def get_assignment(db: Session, assignment_id: str, user_id: str) -> Assignment:
    a = db.query(Assignment).filter(
        Assignment.id == assignment_id,
        Assignment.user_id == user_id,
    ).first()
    if not a:
        raise ValueError("Assignment not found")
    return a

def trigger_n8n_pipeline(assignment: Assignment) -> str:
    """Trigger the n8n assignment_ingest_workflow and return execution ID."""
    payload = {
        "assignment_id": str(assignment.id),
        "user_id": str(assignment.user_id),
        "title": assignment.title,
        "topic": assignment.topic,
        "instructions": assignment.instructions,
        "focus_area": assignment.focus_area,
        "word_count": assignment.word_count,
        "academic_level": assignment.academic_level,
        "citation_style": assignment.citation_style,
        "delivery_method": assignment.delivery_method,
        "delivery_email": assignment.delivery_email,
        "review_type": assignment.review_type,
    }
    try:
        headers = {"X-N8N-API-KEY": settings.N8N_API_KEY} if settings.N8N_API_KEY else {}
        resp = httpx.post(
            f"{settings.N8N_BASE_URL}/webhook/assignment-ingest",
            json=payload,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("executionId", "queued")
    except Exception as e:
        return f"trigger_failed:{e}"

def update_pipeline_log(db: Session, assignment_id: str, stage: str, result: dict):
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if a:
        log = list(a.pipeline_log or [])
        from datetime import datetime
        log.append({"stage": stage, "result": result, "ts": datetime.utcnow().isoformat()})
        a.pipeline_log = log
        db.commit()
