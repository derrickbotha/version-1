import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class DomGraph(Base):
    __tablename__ = "dom_graphs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site       = Column(String(100), nullable=False)   # e.g. "moodle", "canvas", "blackboard"
    lms_url    = Column(Text)
    page_type  = Column(String(100))    # login, course, assignment, submission
    scraped_at = Column(DateTime, default=datetime.utcnow)
    metadata_  = Column("metadata", JSONB, default=dict)

    selectors  = relationship("DomSelector", back_populates="graph")

class DomSelector(Base):
    __tablename__ = "dom_selectors"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    graph_id   = Column(UUID(as_uuid=True), ForeignKey("dom_graphs.id"), nullable=False)
    key        = Column(String(100))    # e.g. "upload_button", "save_button"
    selector   = Column(Text)          # e.g. "input[name='repo_upload_file']"
    selector_type = Column(String(30), default="css")  # css, xpath, id
    fallbacks  = Column(JSONB, default=list)
    last_verified = Column(DateTime, default=datetime.utcnow)

    graph = relationship("DomGraph", back_populates="selectors")
