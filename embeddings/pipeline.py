"""
Vector Embedding Pipeline
Converts research paper text into semantic vector embeddings
stored in pgvector for fast similarity search.
"""
import httpx
import os
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EMBEDDING_API_KEY = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://api.deepseek.com/embeddings")
EMBEDDING_DIM     = 1536
CHUNK_SIZE        = 500   # tokens (approx 375 words)

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Split text into overlapping chunks of approximately chunk_size tokens."""
    words = text.split()
    chunks = []
    step = int(chunk_size * 0.8)  # 20% overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def get_embedding(text: str) -> List[float]:
    """Get a vector embedding for a text chunk."""
    if not EMBEDDING_API_KEY:
        logger.warning("No embedding API key — returning zero vector")
        return [0.0] * EMBEDDING_DIM

    try:
        resp = httpx.post(
            EMBEDDING_API_URL,
            json={"model": "text-embedding-ada-002", "input": text},
            headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return [0.0] * EMBEDDING_DIM

def index_paper(db: Session, paper_id: str, text: str, metadata: dict = None) -> int:
    """
    Index a research paper:
    1. Chunk the text
    2. Get embeddings for each chunk
    3. Store in research_embeddings table
    Returns the number of chunks indexed.
    """
    from api.models.research import ResearchEmbedding
    from pgvector.sqlalchemy import Vector

    chunks = chunk_text(text)
    count = 0

    for idx, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        rec = ResearchEmbedding(
            paper_id=paper_id,
            chunk_text=chunk,
            chunk_index=idx,
            embedding=embedding,
            metadata_=metadata or {},
        )
        db.add(rec)
        count += 1

    db.commit()
    logger.info(f"Indexed {count} chunks for paper {paper_id}")
    return count

def semantic_search(db: Session, query: str, top_k: int = 10,
                    threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find research chunks most semantically similar to a query.
    Uses pgvector cosine similarity.
    """
    query_vec = get_embedding(query)

    results = db.execute(
        """
        SELECT id, paper_id, chunk_text,
               1 - (embedding <=> :vec::vector) AS similarity,
               metadata
        FROM research_embeddings
        WHERE 1 - (embedding <=> :vec::vector) > :threshold
        ORDER BY embedding <=> :vec::vector
        LIMIT :k
        """,
        {"vec": query_vec, "threshold": threshold, "k": top_k},
    ).fetchall()

    return [
        {"id": str(r.id), "paper_id": str(r.paper_id),
         "chunk_text": r.chunk_text, "similarity": r.similarity,
         "metadata": r.metadata}
        for r in results
    ]
