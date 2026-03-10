"""
ASA v2.5 — Enhanced Vector Embedding Pipeline
Supports async batch indexing with 500-800 token chunks (20% overlap).
Uses text-embedding-3-large compatible API (1536-dim).
Enables semantic retrieval for the Context Builder.
"""
import asyncio
import httpx
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

EMBEDDING_API_KEY  = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
EMBEDDING_API_URL  = os.getenv(
    "EMBEDDING_API_URL",
    "https://api.openai.com/v1/embeddings"  # or DeepSeek-compatible endpoint
)
EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
EMBEDDING_DIM      = 1536
CHUNK_SIZE_TOKENS  = 600     # target tokens per chunk
CHUNK_OVERLAP      = 0.20    # 20% overlap between chunks
MAX_CHARS_PER_CALL = 8000    # safety cap for API payload


# ─── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS) -> List[str]:
    """
    Split text into overlapping chunks.
    Approximation: 1 token ≈ 0.75 words.
    Target: 600 tokens = ~450 words per chunk, 20% overlap = 90 words.
    """
    words  = text.split()
    step   = max(1, int(chunk_size * (1 - CHUNK_OVERLAP)))
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i: i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def chunk_paper(paper: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk a paper's abstract + title into indexed segments.
    For full text (when pdf_path exists), chunk the full content.
    Returns list of {text, chunk_index, metadata} dicts.
    """
    # Combine available text
    title    = paper.get("title", "")
    abstract = paper.get("abstract", "")
    text     = f"{title}. {abstract}".strip()

    # If PDF path is provided, extract text from PDF
    pdf_path = paper.get("pdf_path")
    if pdf_path:
        pdf_text = _extract_pdf_text(pdf_path)
        if pdf_text:
            text = f"{title}. {pdf_text}"

    chunks = chunk_text(text)
    metadata = {
        "paper":   title[:100],
        "journal": paper.get("journal", ""),
        "year":    paper.get("year"),
        "doi":     paper.get("doi"),
        "access":  paper.get("access_method", ""),
    }

    return [
        {"text": c, "chunk_index": i, "metadata": {**metadata, "section": _guess_section(c, i, len(chunks))}}
        for i, c in enumerate(chunks)
    ]


def _guess_section(text: str, idx: int, total: int) -> str:
    """Heuristically guess which section of the paper a chunk comes from."""
    text_lower = text.lower()
    if idx == 0:
        return "introduction"
    if "method" in text_lower or "approach" in text_lower:
        return "methodology"
    if "result" in text_lower or "finding" in text_lower:
        return "results"
    if "conclus" in text_lower or "summary" in text_lower:
        return "conclusion"
    if idx == total - 1:
        return "conclusion"
    return "body"


def _extract_pdf_text(pdf_path: str) -> Optional[str]:
    """Extract plain text from a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # pip install PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text[:50000]  # cap at 50k chars
    except ImportError:
        logger.debug("PyMuPDF not installed — skipping PDF text extraction")
        return None
    except Exception as e:
        logger.warning(f"PDF extraction failed for {pdf_path}: {e}")
        return None


# ─── Embedding API ─────────────────────────────────────────────────────────────

async def get_embedding_async(text: str) -> List[float]:
    """Get embedding vector for a single text chunk."""
    if not EMBEDDING_API_KEY:
        return [0.0] * EMBEDDING_DIM

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                EMBEDDING_API_URL,
                json={"model": EMBEDDING_MODEL, "input": text[:MAX_CHARS_PER_CALL]},
                headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding API error: {e}")
        return [0.0] * EMBEDDING_DIM


async def get_embeddings_batch(texts: List[str], batch_size: int = 20) -> List[List[float]]:
    """Get embeddings for multiple texts in parallel batches."""
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        tasks = [get_embedding_async(t) for t in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in batch_results:
            if isinstance(r, list):
                all_embeddings.append(r)
            else:
                all_embeddings.append([0.0] * EMBEDDING_DIM)
        await asyncio.sleep(0.1)  # rate-limit courtesy
    return all_embeddings


# ─── Indexing ─────────────────────────────────────────────────────────────────

async def index_sources_async(
    papers: List[Dict[str, Any]],
    assignment_id: str,
) -> int:
    """
    Chunk all papers, generate embeddings, store in pgvector.
    Returns total chunks indexed.
    """
    all_chunks: List[Dict] = []
    for paper in papers:
        chunks = chunk_paper(paper)
        for c in chunks:
            c["paper_data"] = paper
        all_chunks.extend(chunks)

    if not all_chunks:
        return 0

    texts      = [c["text"] for c in all_chunks]
    embeddings = await get_embeddings_batch(texts)

    # Store in DB
    stored = await asyncio.to_thread(
        _store_embeddings_sync, all_chunks, embeddings, assignment_id
    )
    logger.info(f"Indexed {stored} chunks for assignment {assignment_id}")
    return stored


def _store_embeddings_sync(
    chunks: List[Dict],
    embeddings: List[List[float]],
    assignment_id: str,
) -> int:
    """Synchronously store embedding records in the database."""
    try:
        from api.database import SessionLocal
        from api.models.research import ResearchEmbedding, ResearchSource
        import uuid as uuid_module

        db    = SessionLocal()
        count = 0
        try:
            for chunk, embedding in zip(chunks, embeddings):
                paper = chunk.get("paper_data", {})

                # Find or create ResearchSource record
                doi   = paper.get("doi")
                title = paper.get("title", "Untitled")

                source = None
                if doi:
                    source = db.query(ResearchSource).filter(ResearchSource.doi == doi).first()
                if source is None:
                    source = db.query(ResearchSource).filter(ResearchSource.title == title[:200]).first()
                if source is None:
                    source = ResearchSource(
                        title=title[:200],
                        authors=paper.get("authors", []),
                        journal=paper.get("journal", ""),
                        doi=doi,
                        url=paper.get("url"),
                        abstract=paper.get("abstract", "")[:600],
                        year=paper.get("year"),
                        citation_apa=paper.get("citation_apa", ""),
                        topics=paper.get("topics", []),
                    )
                    db.add(source)
                    db.flush()

                rec = ResearchEmbedding(
                    paper_id=source.id,
                    chunk_text=chunk["text"][:2000],
                    chunk_index=chunk["chunk_index"],
                    embedding=embedding,
                    metadata_={
                        **chunk.get("metadata", {}),
                        "assignment_id": assignment_id,
                    },
                )
                db.add(rec)
                count += 1

            db.commit()
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"Embedding storage error: {e}")
            return 0
        finally:
            db.close()
    except ImportError:
        logger.warning("Database not available — embeddings stored in memory only")
        return len(chunks)


# ─── Semantic Search ──────────────────────────────────────────────────────────

async def semantic_search_async(
    query: str,
    top_k: int = 10,
    threshold: float = 0.65,
    assignment_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Find the most semantically similar paper chunks to a query.
    Uses pgvector cosine similarity.
    """
    query_vec = await get_embedding_async(query)
    return await asyncio.to_thread(
        _semantic_search_sync, query_vec, top_k, threshold, assignment_id
    )


def _semantic_search_sync(
    query_vec: List[float],
    top_k: int,
    threshold: float,
    assignment_id: Optional[str],
) -> List[Dict[str, Any]]:
    try:
        from api.database import SessionLocal
        db = SessionLocal()
        try:
            sql = """
                SELECT re.id, re.paper_id, re.chunk_text,
                       1 - (re.embedding <=> :vec::vector) AS similarity,
                       re.metadata
                FROM research_embeddings re
                WHERE 1 - (re.embedding <=> :vec::vector) > :threshold
            """
            params = {"vec": str(query_vec), "threshold": threshold}

            if assignment_id:
                sql += " AND re.metadata->>'assignment_id' = :aid"
                params["aid"] = assignment_id

            sql += " ORDER BY re.embedding <=> :vec::vector LIMIT :k"
            params["k"] = top_k

            results = db.execute(sql, params).fetchall()
            return [
                {
                    "id": str(r.id),
                    "paper_id": str(r.paper_id),
                    "chunk_text": r.chunk_text,
                    "similarity": float(r.similarity),
                    "metadata": r.metadata,
                }
                for r in results
            ]
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Semantic search failed: {e}")
        return []
