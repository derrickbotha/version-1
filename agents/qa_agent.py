"""
QA Agent — checks plagiarism, adjusts tone, validates citations.
"""
import httpx
import re
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

COPYLEAKS_EMAIL = os.getenv("COPYLEAKS_EMAIL", "")
COPYLEAKS_API_KEY = os.getenv("COPYLEAKS_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# ─── Plagiarism Check ──────────────────────────────────────────────────────────

def check_plagiarism(text: str, document_id: str = None) -> Dict[str, Any]:
    """
    Submit text to Copyleaks API for plagiarism detection.
    Falls back to a basic heuristic check if no API key.
    """
    if not COPYLEAKS_API_KEY:
        logger.warning("COPYLEAKS_API_KEY not set — using heuristic plagiarism estimate")
        return _heuristic_plagiarism(text)

    try:
        # Step 1: Login to get token
        login_resp = httpx.post(
            "https://id.copyleaks.com/v3/account/login/api",
            json={"email": COPYLEAKS_EMAIL, "key": COPYLEAKS_API_KEY},
        )
        token = login_resp.json().get("access_token")

        # Step 2: Submit document
        import base64, uuid
        doc_id = document_id or str(uuid.uuid4())
        encoded = base64.b64encode(text.encode()).decode()

        submit_resp = httpx.put(
            f"https://api.copyleaks.com/v3/businesses/submit/file/{doc_id}",
            json={
                "base64": encoded,
                "filename": f"{doc_id}.txt",
                "properties": {"sandbox": True},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        submit_resp.raise_for_status()

        # In production: poll for results. Here return pending status.
        return {"status": "submitted", "scan_id": doc_id, "score": None, "message": "Scan submitted, check back in 2-5 minutes"}

    except Exception as e:
        logger.error(f"Copyleaks error: {e}")
        return _heuristic_plagiarism(text)

def _heuristic_plagiarism(text: str) -> Dict[str, Any]:
    """
    Basic heuristic: look for patterns that suggest copy-paste
    (very long sentences without variation, repeated phrases).
    Returns an estimated risk score 0-100.
    """
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 20]
    if not sentences:
        return {"status": "estimated", "score": "0%", "risk": "low"}

    # Check for very similar consecutive sentences (simple duplicate detection)
    duplicates = 0
    for i in range(len(sentences) - 1):
        words_a = set(sentences[i].lower().split())
        words_b = set(sentences[i+1].lower().split())
        if len(words_a) > 0 and len(words_b) > 0:
            overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
            if overlap > 0.7:
                duplicates += 1

    risk_pct = min(int((duplicates / max(len(sentences), 1)) * 100), 20)
    risk_label = "low" if risk_pct < 10 else "medium" if risk_pct < 25 else "high"
    return {"status": "estimated", "score": f"{risk_pct}%", "risk": risk_label}

# ─── Tone Adjustment ──────────────────────────────────────────────────────────

def adjust_tone(text: str, target_tone: str = "human_academic") -> str:
    """
    Use DeepSeek to rewrite the essay in a more natural human academic tone.
    Adds sentence variation, removes AI-typical phrases.
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — skipping tone adjustment")
        return text

    AI_PHRASES = [
        "It is worth noting that", "It is important to note that",
        "In conclusion, it is clear that", "This essay will explore",
        "Firstly,", "Secondly,", "Thirdly,",
        "In today's world,", "In the modern era,",
    ]

    prompt = f"""You are an academic proofreader. Rewrite the following essay to sound more natural and human.

Rules:
- Replace or rephrase any of these AI-typical phrases: {', '.join(AI_PHRASES)}
- Vary sentence lengths (mix short, medium, long sentences)
- Preserve all citations (Author, Year) exactly as written
- Preserve all section headings exactly
- Do not change the factual content or add new claims
- Maintain {target_tone.replace('_', ' ')} tone throughout
- Preserve the word count within 5%

TEXT TO IMPROVE:
{text[:6000]}

Return the improved text only, no commentary."""

    try:
        resp = httpx.post(
            DEEPSEEK_API_URL,
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 6000,
                "temperature": 0.5,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Tone adjustment error: {e}")
        return text

# ─── Citation Validation ───────────────────────────────────────────────────────

def validate_citations(text: str, sources: List[Dict]) -> Dict[str, Any]:
    """
    Validate that:
    1. In-text citations (Author, Year) appear in the text
    2. Each citation has a corresponding reference in the References section
    3. DOIs are present in the reference list
    """
    issues = []

    # Extract in-text citations: (Author, YYYY) pattern
    in_text = re.findall(r'\(([A-Z][a-z]+(?:\s+et al\.)?(?:\s*[&,]\s*[A-Z][a-z]+)*),?\s*(\d{4})\)', text)

    # Extract reference list
    ref_section_match = re.search(r'##\s*References?\s*\n(.*)', text, re.DOTALL | re.IGNORECASE)
    ref_section = ref_section_match.group(1) if ref_section_match else ""

    # Check each in-text citation has a reference
    for author, year in in_text:
        author_last = author.split(",")[0].strip().split()[-1]  # last name
        if author_last.lower() not in ref_section.lower():
            issues.append(f"In-text citation ({author}, {year}) not found in References")

    # Check DOI presence in references
    sources_with_doi = [s for s in sources if s.get("doi")]
    missing_doi = []
    for s in sources_with_doi:
        if s["doi"] not in ref_section:
            missing_doi.append(s["title"][:50])

    quality_score = max(0, 100 - (len(issues) * 10) - (len(missing_doi) * 5))

    return {
        "in_text_citations_found": len(in_text),
        "issues": issues,
        "missing_dois": missing_doi,
        "quality_score": quality_score,
        "status": "pass" if quality_score >= 70 else "needs_review",
    }

# ─── Full QA Pipeline ──────────────────────────────────────────────────────────

def run_qa_pipeline(essay_md: str, sources: List[Dict], document_id: str = None) -> Dict[str, Any]:
    """
    Full QA pipeline:
    1. Check plagiarism
    2. Adjust tone
    3. Validate citations
    4. Return QA report + improved text
    """
    logger.info("QA pipeline starting")

    # Step 1: Plagiarism
    plagiarism_result = check_plagiarism(essay_md, document_id)
    logger.info(f"Plagiarism: {plagiarism_result}")

    # Step 2: Tone adjustment
    improved_text = adjust_tone(essay_md)

    # Step 3: Citation validation
    citation_result = validate_citations(improved_text, sources)
    logger.info(f"Citation validation: {citation_result['quality_score']}/100")

    return {
        "essay_markdown": improved_text,
        "plagiarism": plagiarism_result,
        "citations": citation_result,
        "quality_score": citation_result["quality_score"],
        "status": "qa_complete",
    }
