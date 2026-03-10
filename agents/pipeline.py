"""
Full ASA v2 pipeline orchestrator.
Called by n8n or directly for testing.
"""
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.research_agent  import run_research_pipeline
from agents.writing_agent   import run_writing_pipeline
from agents.qa_agent        import run_qa_pipeline
from agents.delivery_agent  import run_delivery_pipeline

logger = logging.getLogger(__name__)

def run_full_pipeline(job: dict) -> dict:
    """
    Execute the complete ASA v2 pipeline for one assignment.

    job dict keys:
        assignment_id, title, topic, instructions, focus_area,
        word_count, academic_level, citation_style,
        delivery_method, delivery_email,
        lms_url, lms_username, lms_password,
        student_name, module_code
    """
    assignment_id  = job["assignment_id"]
    title          = job["title"]
    topic          = job["topic"]
    instructions   = job.get("instructions", "")
    focus_area     = job.get("focus_area", "")
    word_count     = int(job.get("word_count", 2000))
    academic_level = job.get("academic_level", "undergraduate")
    citation_style = job.get("citation_style", "Harvard")
    delivery_method= job.get("delivery_method", "download")
    delivery_email = job.get("delivery_email")
    lms_url        = job.get("lms_url")
    lms_username   = job.get("lms_username")
    lms_password   = job.get("lms_password")
    student_name   = job.get("student_name", "Student")
    module_code    = job.get("module_code", "")

    report = {"assignment_id": assignment_id, "stages": []}

    try:
        # ── Stage 1: Research ──
        logger.info(f"[{assignment_id}] Stage 1: Research")
        research = run_research_pipeline(topic, focus_area, academic_level)
        report["stages"].append({"stage": "research", "status": "ok", "sources": research["source_count"]})

        # ── Stage 2: Writing ──
        logger.info(f"[{assignment_id}] Stage 2: Writing")
        writing = run_writing_pipeline(
            title=title, topic=topic, instructions=instructions,
            focus_area=focus_area, word_count=word_count,
            academic_level=academic_level, citation_style=citation_style,
            sources=research["sources"],
        )
        report["stages"].append({"stage": "writing", "status": "ok", "words": writing["word_count"]})

        # ── Stage 3: QA ──
        logger.info(f"[{assignment_id}] Stage 3: QA")
        qa = run_qa_pipeline(writing["essay_markdown"], research["sources"], assignment_id)
        report["stages"].append({"stage": "qa", "status": "ok", "quality": qa["quality_score"]})

        # ── Stage 4: Delivery ──
        logger.info(f"[{assignment_id}] Stage 4: Delivery")
        delivery = run_delivery_pipeline(
            essay_md=qa["essay_markdown"],
            title=title, student_name=student_name,
            module_code=module_code, assignment_id=assignment_id,
            delivery_method=delivery_method, delivery_email=delivery_email,
            lms_url=lms_url, lms_username=lms_username, lms_password=lms_password,
        )
        report["stages"].append({"stage": "delivery", "status": delivery.get("status")})

        report["status"]          = "completed"
        report["docx_path"]       = delivery.get("docx_path")
        report["plagiarism_score"]= str(qa["plagiarism"].get("score", ""))
        report["quality_score"]   = qa["quality_score"]
        return report

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        report["status"] = "failed"
        report["error"]  = str(e)
        return report

if __name__ == "__main__":
    # Quick test run
    import json
    result = run_full_pipeline({
        "assignment_id": "test-001",
        "title": "Data Repositories in Data Ecology",
        "topic": "Research data repositories for data science and data ecology",
        "focus_area": "Open access repositories and FAIR data principles",
        "word_count": 1500,
        "academic_level": "undergraduate",
        "citation_style": "Harvard",
        "delivery_method": "download",
        "student_name": "Test Student",
        "module_code": "DS7001",
    })
    print(json.dumps(result, indent=2))
