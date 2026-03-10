import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from ..database import Base

class ResearchSource(Base):
    __tablename__ = "research_sources"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title        = Column(Text, nullable=False)
    authors      = Column(JSONB, default=list)
    journal      = Column(String(500))
    doi          = Column(String(255), unique=True, index=True)
    url          = Column(Text)
    abstract     = Column(Text)
    year         = Column(Integer)
    citation_apa = Column(Text)
    topics       = Column(JSONB, default=list)
    methods      = Column(JSONB, default=list)
    full_text    = Column(Text)
    created_at   = Column(DateTime, default=datetime.utcnow)

    embeddings   = relationship("ResearchEmbedding", back_populates="source")
    kg_node      = relationship("KnowledgeGraphNode", back_populates="source", uselist=False)

class ResearchEmbedding(Base):
    __tablename__ = "research_embeddings"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paper_id       = Column(UUID(as_uuid=True), ForeignKey("research_sources.id"), nullable=False)
    chunk_text     = Column(Text, nullable=False)
    chunk_index    = Column(Integer)
    embedding      = Column(Vector(1536))   # OpenAI-compatible 1536-dim; DeepSeek uses same
    metadata_      = Column("metadata", JSONB, default=dict)
    created_at     = Column(DateTime, default=datetime.utcnow)

    source = relationship("ResearchSource", back_populates="embeddings")

class KnowledgeGraphNode(Base):
    __tablename__ = "kg_nodes"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id   = Column(UUID(as_uuid=True), ForeignKey("research_sources.id"), nullable=True)
    node_type   = Column(String(50))    # Paper, Author, Institution, Method, Dataset, Topic, Journal
    name        = Column(Text, nullable=False)
    properties  = Column(JSONB, default=dict)
    created_at  = Column(DateTime, default=datetime.utcnow)

    source      = relationship("ResearchSource", back_populates="kg_node")
    out_edges   = relationship("KnowledgeGraphEdge", foreign_keys="KnowledgeGraphEdge.source_node_id", back_populates="source_node")
    in_edges    = relationship("KnowledgeGraphEdge", foreign_keys="KnowledgeGraphEdge.target_node_id", back_populates="target_node")

class KnowledgeGraphEdge(Base):
    __tablename__ = "kg_edges"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("kg_nodes.id"), nullable=False)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("kg_nodes.id"), nullable=False)
    edge_type      = Column(String(100))    # AUTHORED_BY, CITES, USES_METHOD, RELATED_TO_TOPIC, etc.
    weight         = Column(Float, default=1.0)
    properties     = Column(JSONB, default=dict)
    created_at     = Column(DateTime, default=datetime.utcnow)

    source_node = relationship("KnowledgeGraphNode", foreign_keys=[source_node_id], back_populates="out_edges")
    target_node = relationship("KnowledgeGraphNode", foreign_keys=[target_node_id], back_populates="in_edges")
