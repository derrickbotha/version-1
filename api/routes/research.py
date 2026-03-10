from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas.research import ResearchSourceOut, KGNodeOut
from ..services.auth_service import get_current_user
from ..models.research import ResearchSource, KnowledgeGraphNode, KnowledgeGraphEdge

router = APIRouter(prefix="/research", tags=["research"])

def current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    try:
        return get_current_user(token, db)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/sources", response_model=List[ResearchSourceOut])
def list_sources(topic: str = Query(None), limit: int = 20,
                 user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(ResearchSource)
    if topic:
        q = q.filter(ResearchSource.topics.contains([topic]))
    return q.order_by(ResearchSource.created_at.desc()).limit(limit).all()

@router.get("/graph/nodes", response_model=List[KGNodeOut])
def list_graph_nodes(node_type: str = Query(None), limit: int = 50,
                     user=Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(KnowledgeGraphNode)
    if node_type:
        q = q.filter(KnowledgeGraphNode.node_type == node_type)
    return q.limit(limit).all()

@router.get("/graph/stats")
def graph_stats(user=Depends(current_user), db: Session = Depends(get_db)):
    nodes = db.query(KnowledgeGraphNode).count()
    edges = db.query(KnowledgeGraphEdge).count()
    sources = db.query(ResearchSource).count()
    return {"total_nodes": nodes, "total_edges": edges, "total_sources": sources}
