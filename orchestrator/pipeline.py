"""
ASA v2.5 — Python-Orchestrated Parallel Agentic Pipeline
Pure asyncio orchestration. No n8n dependency.

Execution order:
    1. Assignment Analysis Agent
    2. Query Expansion Engine
    3. Parallel Research (Institutional + Web agents, concurrent)
    4. Source Normalisation & DOI Extraction
    5. Access Intelligence Classification
    6. Knowledge Graph Storage
    7. Vector Embeddings Generation
    8. Context Builder
    9. Writing Agent (DeepSeek)
    10. Document Generator (Markdown → DOCX)
    11. QA Agent (plagiarism + citation + tone)
    12. Professor Review Branch (optional)
    13. Delivery
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Dict, List, Optional

from orchestrator.analysis_agent import analyze_assignment
from orchestrator.query_expansion import expand_queries
from orchestrator.context_builder import build_context

from agents.research.web_agent import run_web_agent_async
from agents.research.institutional_agent import run_institutional_agent_async
from agents.research.normalizer import normalize_sources
from agents.research.access_classifier import classify_access

from agents.writing_agent import run_writing_pipeline
from agents.qa_agent import run_qa_pipeline
from agents.delivery_agent import run_delivery_pipeline

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5   # seconds


# ─── Retry wrapper ─────────────────────────────────────────────────────────────

async def _with_retry(coro_fn, stage_name: str, *args, **kwargs):
    """Run an async coroutine with up to MAX_RETRIES attempts."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            logger.warning(
                f"[{stage_name}] Attempt {attempt}/{MAX_RETRIES} failed: {e}"
            )
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * attempt)
    logger.error(f"[{stage_name}] All {MAX_RETRIES} retries exhausted: {last_exc}")
    raise last_exc


# ─── Stage functions (async wrappers) ──────────────────────────────────────────

async def _stage_research(queries: Dict, credentials: Optional[Dict]) -> List[Dict]:
    """Run Institutional + Web agents in PARALLEL using asyncio.gather."""
    all_queries = queries.get("all_queries", [])
    keyword_queries = queries.get("keyword_queries", [])
    boolean_queries = queries.get("boolean_queries", [])

    tasks = [
        _with_retry(run_web_agent_async, "WebAgent", all_queries, queries),
    ]

    if credentials:
        tasks.append(
            _with_retry(
                run_institutional_agent_async,
                "InstitutionalAgent",
                boolean_queries or keyword_queries,
                credentials,
            )
        )

    logger.info(f"Running {len(tasks)} research agents in parallel...")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: List[Dict] = []
    for i, result in enumerate(results):
        agent_name = ["WebAgent", "InstitutionalAgent"][i] if len(tasks) > 1 else "WebAgent"
        if isinstance(result, Exception):
            logger.error(f"[{agent_name}] Failed: {result}")
        elif isinstance(result, list):
            logger.info(f"[{agent_name}] Retrieved {len(result)} papers")
            merged.extend(result)

    # Deduplicate by DOI
    seen_dois: set = set()
    unique: List[Dict] = []
    for p in merged:
        doi = p.get("doi")
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        unique.append(p)

    logger.info(f"Merged & deduplicated: {len(unique)} unique papers")
    return unique


async def _stage_embeddings(sources: List[Dict], assignment_id: str) -> bool:
    """Generate and store vector embeddings for all sources."""
    try:
        from embeddings.pipeline import index_sources_async
        await index_sources_async(sources, assignment_id)
        return True
    except Exception as e:
        logger.warning(f"Embeddings generation failed (non-fatal): {e}")
        return False


async def _stage_knowledge_graph(sources: List[Dict], analysis: Dict) -> bool:
    """Store papers, authors, journals, methods in the knowledge graph."""
    try:
        from knowledge_graph.graph_service import upsert_research_batch
        await upsert_research_batch(sources, analysis)
        return True
    except Exception as e:
        logger.warning(f"Knowledge graph update failed (non-fatal): {e}")
        return False


# ─── Main pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the complete ASA v2.5 pipeline for one assignment.

    job dict keys:
        assignment_id, title, topic, instructions, focus_area,
        word_count, academic_level, citation_style, module_code,
        delivery_method, delivery_email,
        lms_url, lms_username, lms_password,
        student_name,
        institutional_username, institutional_password,
        review_type,
        status_callback   (optional async callable: fn(stage, status, data))
    """
    assignment_id   = job["assignment_id"]
    title           = job["title"]
    topic           = job["topic"]
    instructions    = job.get("instructions", "")
    focus_area      = job.get("focus_area")
    word_count      = int(job.get("word_count", 2000))
    academic_level  = job.get("academic_level", "undergraduate")
    citation_style  = job.get("citation_style", "Harvard")
    module_code     = job.get("module_code")
    student_name    = job.get("student_name", "Student")
    delivery_method = job.get("delivery_method", "download")
    delivery_email  = job.get("delivery_email")
    lms_url         = job.get("lms_url")
    lms_username    = job.get("lms_username")
    lms_password    = job.get("lms_password")
    review_type     = job.get("review_type", "agent_only")
    status_callback = job.get("status_callback")

    # Institutional credentials (optional — enables ScienceDirect/Scopus/etc.)
    inst_credentials = None
    if job.get("institutional_username") and job.get("institutional_password"):
        inst_credentials = {
            "username": job["institutional_username"],
            "password": job["institutional_password"],
            "institution": job.get("institution", ""),
        }

    report = {
        "assignment_id": assignment_id,
        "stages": [],
        "start_time": time.time(),
    }

    async def _notify(stage: str, status: str, data: Dict = None):
        entry = {"stage": stage, "status": status, "data": data or {}}
        report["stages"].append(entry)
        logger.info(f"[{assignment_id}] {stage}: {status}")
        if status_callback:
            try:
                await status_callback(stage, status, data or {})
            except Exception:
                pass

    try:
        # ── Stage 1: Assignment Analysis ───────────────────────────────────
        await _notify("analysis", "running")
        analysis = analyze_assignment(
            title=title, topic=topic, instructions=instructions,
            focus_area=focus_area, word_count=word_count,
            academic_level=academic_level, citation_style=citation_style,
            module_code=module_code,
        )
        await _notify("analysis", "complete", {
            "keywords": analysis["keywords"],
            "required_sources": analysis["required_sources"],
        })

        # ── Stage 2: Query Expansion ──────────────────────────────────────
        await _notify("query_expansion", "running")
        queries = expand_queries(analysis)
        await _notify("query_expansion", "complete", {
            "total_queries": len(queries.get("all_queries", [])),
        })

        # ── Stage 3: Parallel Research ────────────────────────────────────
        await _notify("research", "running", {
            "agents": ["web_agent"] + (["institutional_agent"] if inst_credentials else []),
        })
        raw_papers = await _with_retry(
            _stage_research, "Research", queries, inst_credentials
        )
        await _notify("research", "complete", {"papers_found": len(raw_papers)})

        # ── Stage 4: Source Normalisation & DOI Extraction ────────────────
        await _notify("normalisation", "running")
        normalized = await asyncio.to_thread(normalize_sources, raw_papers)
        await _notify("normalisation", "complete", {"papers_normalized": len(normalized)})

        # ── Stage 5: Access Intelligence Classification ───────────────────
        await _notify("access_classification", "running")
        classified = await asyncio.to_thread(classify_access, normalized)
        await _notify("access_classification", "complete", {
            "open_access": sum(1 for p in classified if p.get("access_method") == "OPEN_ACCESS"),
            "institutional": sum(1 for p in classified if p.get("access_method") == "INSTITUTIONAL"),
        })

        # ── Stages 6 & 7 run in parallel (non-blocking) ───────────────────
        await _notify("knowledge_graph", "running")
        await _notify("embeddings", "running")

        kg_task  = asyncio.create_task(_stage_knowledge_graph(classified, analysis))
        emb_task = asyncio.create_task(_stage_embeddings(classified, assignment_id))
        kg_ok, emb_ok = await asyncio.gather(kg_task, emb_task)

        await _notify("knowledge_graph", "complete" if kg_ok else "skipped")
        await _notify("embeddings", "complete" if emb_ok else "skipped")

        # ── Stage 8: Context Builder ──────────────────────────────────────
        await _notify("context_building", "running")
        context = await asyncio.to_thread(build_context, classified, analysis)
        await _notify("context_building", "complete", {
            "themes": context["themes"],
            "key_papers": len(context["key_papers"]),
        })

        # ── Stage 9: Writing Agent ────────────────────────────────────────
        await _notify("writing", "running")
        writing_result = await asyncio.to_thread(
            run_writing_pipeline,
            title=title,
            topic=topic,
            instructions=instructions,
            focus_area=focus_area,
            word_count=word_count,
            academic_level=academic_level,
            citation_style=citation_style,
            sources=context["formatted_sources"],
            context=context,
        )
        await _notify("writing", "complete", {"word_count": writing_result["word_count"]})

        # ── Stage 10: QA Agent ────────────────────────────────────────────
        await _notify("qa", "running")
        qa_result = await asyncio.to_thread(
            run_qa_pipeline,
            writing_result["essay_markdown"],
            classified,
            assignment_id,
        )
        await _notify("qa", "complete", {
            "quality_score": qa_result["quality_score"],
            "plagiarism": qa_result["plagiarism"].get("score"),
        })

        # ── Stage 11: Professor Review (optional pause) ───────────────────
        if review_type == "agent_professor":
            await _notify("professor_review", "pending")
            # In production: pause here, wait for webhook callback
            # For now: log and continue
            logger.info(f"[{assignment_id}] Professor review queued — awaiting approval")

        # ── Stage 12: Delivery ────────────────────────────────────────────
        await _notify("delivery", "running")
        delivery_result = await asyncio.to_thread(
            run_delivery_pipeline,
            essay_md=qa_result["essay_markdown"],
            title=title,
            student_name=student_name,
            module_code=module_code or "",
            assignment_id=assignment_id,
            delivery_method=delivery_method,
            delivery_email=delivery_email,
            lms_url=lms_url,
            lms_username=lms_username,
            lms_password=lms_password,
        )
        await _notify("delivery", delivery_result.get("status", "complete"), {
            "docx_path": delivery_result.get("docx_path"),
        })

        # ── Final report ──────────────────────────────────────────────────
        report["status"]           = "completed"
        report["docx_path"]        = delivery_result.get("docx_path")
        report["plagiarism_score"] = str(qa_result["plagiarism"].get("score", ""))
        report["quality_score"]    = qa_result["quality_score"]
        report["sources_used"]     = len(classified)
        report["elapsed_seconds"]  = round(time.time() - report["start_time"], 1)
        await _notify("pipeline", "completed", {"elapsed": report["elapsed_seconds"]})
        return report

    except Exception as e:
        logger.error(f"[{assignment_id}] Pipeline fatal error: {e}\n{traceback.format_exc()}")
        report["status"] = "failed"
        report["error"]  = str(e)
        await _notify("pipeline", "failed", {"error": str(e)})
        return report


# ─── Entry point for direct execution ─────────────────────────────────────────

if __name__ == "__main__":
    import json

    async def _test():
        result = await run_pipeline({
            "assignment_id": "test-v25-001",
            "title": "AI Pricing in Insurance",
            "topic": "Machine learning applications in insurance underwriting and pricing",
            "focus_area": "Focus on algorithmic bias, regulatory compliance, and Kenya/EU contexts",
            "word_count": 3000,
            "academic_level": "postgraduate",
            "citation_style": "APA",
            "module_code": "INS-8001",
            "delivery_method": "download",
            "student_name": "Test Student",
        })
        print(json.dumps(result, indent=2, default=str))

    asyncio.run(_test())
