"""
Knowledge Graph Service
Stores papers, authors, journals, methods, and topics as nodes.
Creates typed edges between them.
Reuses existing nodes to grow the graph over time.

Node types: Paper, Author, Institution, Method, Dataset, Topic, Journal, AccessMethod
Edge types: WRITTEN_BY, PUBLISHED_IN, STUDIES, USES_METHOD, CITES,
            ACCESSIBLE_VIA, RELATED_TO_TOPIC, ASSIGNMENT_USES
"""
import logging
import uuid
import asyncio
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def _get_db():
    """Get a database session. Lazy import to avoid circular deps."""
    try:
        from api.database import SessionLocal
        return SessionLocal()
    except Exception:
        return None


async def upsert_research_batch(
    papers: List[Dict[str, Any]],
    analysis: Dict[str, Any],
) -> Dict[str, int]:
    """
    Async wrapper — runs the synchronous DB operations in a thread pool.
    """
    return await asyncio.to_thread(_upsert_research_batch_sync, papers, analysis)


def _upsert_research_batch_sync(
    papers: List[Dict[str, Any]],
    analysis: Dict[str, Any],
) -> Dict[str, int]:
    """
    Upsert all papers into the knowledge graph.
    Returns counts of nodes and edges created.
    """
    db = _get_db()
    if db is None:
        logger.warning("No database session available — skipping KG update")
        return {"nodes": 0, "edges": 0}

    nodes_created = 0
    edges_created = 0

    try:
        from api.models.research import KnowledgeGraphNode, KnowledgeGraphEdge, ResearchSource

        for paper in papers:
            try:
                # ── 1. Upsert Paper node ───────────────────────────────────────────
                paper_node = _upsert_node(
                    db, KnowledgeGraphNode,
                    node_type="Paper",
                    name=paper.get("title", "Untitled")[:200],
                    properties={
                        "doi":           paper.get("doi"),
                        "year":          paper.get("year"),
                        "journal":       paper.get("journal"),
                        "abstract":      (paper.get("abstract") or "")[:300],
                        "access_method": paper.get("access_method"),
                        "citation_count": paper.get("citation_count", 0),
                        "url":           paper.get("url"),
                    },
                )
                if paper_node is None:
                    continue
                is_new_node = _check_is_new(paper_node)
                if is_new_node:
                    nodes_created += 1

                # ── 2. Author nodes + WRITTEN_BY edges ────────────────────────────
                for author_name in (paper.get("authors") or [])[:8]:
                    if not author_name:
                        continue
                    author_node = _upsert_node(
                        db, KnowledgeGraphNode,
                        node_type="Author",
                        name=author_name[:150],
                        properties={},
                    )
                    if author_node:
                        nodes_created += _create_edge_if_missing(
                            db, KnowledgeGraphEdge,
                            paper_node.id, author_node.id, "WRITTEN_BY"
                        )

                # ── 3. Journal node + PUBLISHED_IN edge ──────────────────────────
                journal = paper.get("journal") or ""
                if journal.strip():
                    journal_node = _upsert_node(
                        db, KnowledgeGraphNode,
                        node_type="Journal",
                        name=journal[:200],
                        properties={"source_type": paper.get("source_type", "journal")},
                    )
                    if journal_node:
                        nodes_created += _create_edge_if_missing(
                            db, KnowledgeGraphEdge,
                            paper_node.id, journal_node.id, "PUBLISHED_IN"
                        )

                # ── 4. Topic nodes + STUDIES edges ────────────────────────────────
                topics = analysis.get("keywords", [])[:5]
                for topic in topics:
                    if not topic:
                        continue
                    topic_node = _upsert_node(
                        db, KnowledgeGraphNode,
                        node_type="Topic",
                        name=topic[:100],
                        properties={"academic_level": analysis.get("academic_level")},
                    )
                    if topic_node:
                        # Only add STUDIES if the topic appears in title or abstract
                        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
                        if topic.lower() in text:
                            nodes_created += _create_edge_if_missing(
                                db, KnowledgeGraphEdge,
                                paper_node.id, topic_node.id, "STUDIES"
                            )

                # ── 5. Method nodes + USES_METHOD edges ───────────────────────────
                method_keywords = [
                    "regression", "meta-analysis", "systematic review",
                    "machine learning", "deep learning", "survey",
                    "qualitative", "quantitative", "case study",
                    "simulation", "experiment", "interview",
                ]
                abstract_lower = (paper.get("abstract") or "").lower()
                for method in method_keywords:
                    if method in abstract_lower:
                        method_node = _upsert_node(
                            db, KnowledgeGraphNode,
                            node_type="Method",
                            name=method.title(),
                            properties={},
                        )
                        if method_node:
                            nodes_created += _create_edge_if_missing(
                                db, KnowledgeGraphEdge,
                                paper_node.id, method_node.id, "USES_METHOD"
                            )

                # ── 6. AccessMethod node + ACCESSIBLE_VIA edge ───────────────────
                access = paper.get("access_method", "WEB_SOURCE")
                access_node = _upsert_node(
                    db, KnowledgeGraphNode,
                    node_type="AccessMethod",
                    name=access,
                    properties={
                        "authentication_required": access not in ("OPEN_ACCESS", "WEB_SOURCE"),
                        "provider": paper.get("_source_agent", ""),
                    },
                )
                if access_node:
                    nodes_created += _create_edge_if_missing(
                        db, KnowledgeGraphEdge,
                        paper_node.id, access_node.id, "ACCESSIBLE_VIA"
                    )

            except Exception as e:
                logger.warning(f"KG: failed to process paper '{paper.get('title','?')[:40]}': {e}")
                db.rollback()
                continue

        db.commit()
        logger.info(f"KG update: {nodes_created} nodes, {edges_created} edges")
        return {"nodes": nodes_created, "edges": edges_created}

    except Exception as e:
        logger.error(f"KG batch upsert failed: {e}")
        db.rollback()
        return {"nodes": 0, "edges": 0}
    finally:
        db.close()


def _upsert_node(db, Model, node_type: str, name: str, properties: dict):
    """Find existing node or create new one."""
    try:
        existing = db.query(Model).filter(
            Model.node_type == node_type,
            Model.name == name,
        ).first()
        if existing:
            return existing
        node = Model(
            node_type=node_type,
            name=name,
            properties=properties,
        )
        db.add(node)
        db.flush()
        return node
    except Exception as e:
        logger.debug(f"Node upsert failed ({node_type}:{name[:30]}): {e}")
        db.rollback()
        return None


def _check_is_new(node) -> bool:
    """Heuristic: node is new if created_at is very recent."""
    from datetime import datetime, timedelta
    if hasattr(node, "created_at") and node.created_at:
        return (datetime.utcnow() - node.created_at).total_seconds() < 5
    return True


def _create_edge_if_missing(db, EdgeModel, source_id, target_id, edge_type: str) -> int:
    """Create an edge if it doesn't already exist. Returns 1 if created, 0 otherwise."""
    try:
        existing = db.query(EdgeModel).filter(
            EdgeModel.source_node_id == source_id,
            EdgeModel.target_node_id == target_id,
            EdgeModel.edge_type == edge_type,
        ).first()
        if existing:
            return 0
        edge = EdgeModel(
            source_node_id=source_id,
            target_node_id=target_id,
            edge_type=edge_type,
        )
        db.add(edge)
        db.flush()
        return 1
    except Exception as e:
        logger.debug(f"Edge creation failed ({edge_type}): {e}")
        db.rollback()
        return 0


def get_graph_stats(db=None) -> Dict[str, Any]:
    """Return node/edge counts and breakdown by type."""
    close_db = False
    if db is None:
        db = _get_db()
        close_db = True
    if db is None:
        return {}
    try:
        from api.models.research import KnowledgeGraphNode, KnowledgeGraphEdge, ResearchSource
        from sqlalchemy import func

        node_counts = dict(
            db.query(KnowledgeGraphNode.node_type, func.count(KnowledgeGraphNode.id))
            .group_by(KnowledgeGraphNode.node_type)
            .all()
        )
        edge_counts = dict(
            db.query(KnowledgeGraphEdge.edge_type, func.count(KnowledgeGraphEdge.id))
            .group_by(KnowledgeGraphEdge.edge_type)
            .all()
        )
        sources = db.query(ResearchSource).count()

        return {
            "total_nodes":   sum(node_counts.values()),
            "total_edges":   sum(edge_counts.values()),
            "total_sources": sources,
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts,
        }
    except Exception as e:
        logger.error(f"Graph stats error: {e}")
        return {}
    finally:
        if close_db:
            db.close()
