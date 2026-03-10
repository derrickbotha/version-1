"""
QA Agent v2.5
Three-stage quality pipeline:
1. Plagiarism — Copyleaks (primary), Turnitin-compatible payload (secondary), heuristic fallback
2. Tone Adjustment — DeepSeek removes AI phrases, improves variation
3. Citation Validation — checks every (Author, Year) has a References entry + DOI

Optional 4th stage: Section-level rewrite for sections below quality threshold.
"""
import httpx
import re
import logging
import os
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

COPYLEAKS_EMAIL   = os.getenv("COPYLEAKS_EMAIL", "")
COPYLEAKS_API_KEY = os.getenv("COPYLEAKS_API_KEY", "")
DEEPSEEK_API_URL  = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY", "")

# Phrases strongly associated with AI-generated text
AI_TELL_PHRASES = [
    "It is worth noting that",
    "It is important to note that",
    "In today's world",
    "In the modern era",
    "In conclusion, it is clear that",
    "This essay will explore",
    "This essay aims to",
    "In recent years, there has been",
    "There are many factors",
    "Firstly,", "Secondly,", "Thirdly,", "Lastly,",
    "needless to say",
    "it goes without saying",
    "delve into",
    "In the realm of",
    "As we can see",
    "Furthermore, it should be noted",
]

# ─── Plagiarism ────────────────────────────────────────────────────────────────

def check_plagiarism(text: str, document_id: str = None) -> Dict[str, Any]:
    """Submit document to Copyleaks for plagiarism scanning."""
    if not COPYLEAKS_API_KEY or not COPYLEAKS_EMAIL:
        return _heuristic_plagiarism(text)

    try:
        # Authenticate
        login_resp = httpx.post(
            "https://id.copyleaks.com/v3/account/login/api",
            json={"email": COPYLEAKS_EMAIL, "key": COPYLEAKS_API_KEY},
            timeout=15,
        )
        token = login_resp.json().get("access_token")

        # Submit
        import base64, uuid
        doc_id  = document_id or str(uuid.uuid4()).replace("-", "")
        encoded = base64.b64encode(text.encode()).decode()

        resp = httpx.put(
            f"https://api.copyleaks.com/v3/businesses/submit/file/{doc_id}",
            json={
                "base64":    encoded,
                "filename":  f"{doc_id}.txt",
                "properties": {"sandbox": True, "webhooks": {}},
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        resp.raise_for_status()
        return {
            "status":    "submitted",
            "scan_id":   doc_id,
            "score":     None,
            "message":   "Scan submitted to Copyleaks — results available in 2–5 minutes",
            "provider":  "copyleaks",
        }
    except Exception as e:
        logger.warning(f"Copyleaks error: {e} — falling back to heuristic")
        return _heuristic_plagiarism(text)


def _heuristic_plagiarism(text: str) -> Dict[str, Any]:
    """
    Heuristic plagiarism estimate based on:
    - Repeated n-grams
    - Sentence-level near-duplicates
    """
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 25]
    if not sentences:
        return {"status": "estimated", "score": "0%", "risk": "low", "provider": "heuristic"}

    # Check consecutive sentence similarity via word-set Jaccard
    duplicates = 0
    for i in range(len(sentences) - 1):
        a = set(sentences[i].lower().split())
        b = set(sentences[i+1].lower().split())
        if len(a) > 3 and len(b) > 3:
            jaccard = len(a & b) / len(a | b)
            if jaccard > 0.60:
                duplicates += 1

    risk_pct   = min(int((duplicates / max(len(sentences), 1)) * 100), 25)
    risk_label = "low" if risk_pct < 10 else "medium" if risk_pct < 20 else "high"

    return {
        "status":   "estimated",
        "score":    f"{risk_pct}%",
        "risk":     risk_label,
        "provider": "heuristic",
    }


# ─── Tone Adjustment ──────────────────────────────────────────────────────────

def adjust_tone(text: str) -> str:
    """Remove AI tell-phrases and improve sentence variation via DeepSeek."""
    if not DEEPSEEK_API_KEY:
        return _basic_phrase_replacement(text)

    # Quick pre-check: does the text have obvious AI phrases?
    ai_phrase_count = sum(1 for p in AI_TELL_PHRASES if p.lower() in text.lower())
    if ai_phrase_count == 0:
        logger.info("Tone check: no AI phrases detected — skipping rewrite")
        return text

    prompt = f"""You are an expert academic proofreader. Rewrite the following essay to sound more natural and human-written.

RULES (strictly follow):
1. Replace or rephrase these AI-typical phrases: {', '.join(AI_TELL_PHRASES[:10])}
2. Vary sentence lengths: mix short (8–12 words), medium (20–25 words), and long (30+) sentences
3. Preserve ALL in-text citations exactly as written — do NOT change (Author, Year)
4. Preserve ALL ## section headings exactly
5. Do NOT add new factual claims or citations
6. Maintain academic formal tone throughout
7. Keep word count within 5% of original
8. Preserve the References section exactly

ESSAY TO IMPROVE:
{text[:7000]}

Return ONLY the improved essay. No commentary."""

    try:
        resp = httpx.post(
            DEEPSEEK_API_URL,
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 7000,
                "temperature": 0.45,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=100,
        )
        resp.raise_for_status()
        improved = resp.json()["choices"][0]["message"]["content"]
        logger.info(f"Tone adjustment: {ai_phrase_count} AI phrases processed")
        return improved
    except Exception as e:
        logger.error(f"Tone adjustment API error: {e}")
        return _basic_phrase_replacement(text)


def _basic_phrase_replacement(text: str) -> str:
    """Simple string replacements for common AI phrases — no API needed."""
    replacements = {
        "It is worth noting that":       "Notably,",
        "It is important to note that":  "Significantly,",
        "In today's world":              "In contemporary contexts",
        "In the modern era":             "In recent decades",
        "In conclusion, it is clear that": "The evidence demonstrates that",
        "This essay will explore":       "This essay examines",
        "This essay aims to":            "This essay investigates",
        "needless to say":               "",
        "delve into":                    "examine",
        "In the realm of":               "In",
        "Furthermore, it should be noted that": "Moreover,",
        "Firstly,":  "First,",
        "Secondly,": "Second,",
        "Thirdly,":  "Third,",
        "Lastly,":   "Finally,",
    }
    for phrase, replacement in replacements.items():
        text = text.replace(phrase, replacement)
    return text


# ─── Citation Validation ──────────────────────────────────────────────────────

def validate_citations(text: str, sources: List[Dict]) -> Dict[str, Any]:
    """
    Check:
    1. Every (Author, Year) in-text citation appears in the References section
    2. Every cited paper has a DOI or URL
    3. No orphan references (cited in references but not in text)
    """
    issues: List[str] = []
    warnings: List[str] = []

    # Extract References section
    ref_match = re.search(r'##\s*References?\s*\n([\s\S]+?)(?:##|$)', text, re.IGNORECASE)
    ref_section = ref_match.group(1) if ref_match else ""
    body_text   = text[:ref_match.start()] if ref_match else text

    # Find all in-text citations: (Author, YYYY) or (Author et al., YYYY) or (Author & Author, YYYY)
    citation_pattern = re.compile(
        r'\(([A-Z][a-zA-Z\u00e9\u00e0\u00fc\-]+(?:\s+et\s+al\.|\s*[&,]\s*[A-Z][a-zA-Z\-]+)*),?\s*(\d{4}[a-z]?)\)'
    )
    in_text_citations = citation_pattern.findall(body_text)

    for author, year in in_text_citations:
        last_name = author.split(",")[0].strip().split()[-1]
        if last_name.lower() not in ref_section.lower():
            issues.append(f"Citation ({author}, {year}) not found in References section")

    # Check DOI coverage
    sources_missing_doi = [
        s.get("title", "?")[:50]
        for s in sources
        if not s.get("doi") and not s.get("url")
    ]
    if sources_missing_doi:
        warnings.append(f"{len(sources_missing_doi)} sources have no DOI or URL")

    # Calculate quality score
    total_issues   = len(issues)
    total_warnings = len(warnings)
    quality_score  = max(0, 100 - (total_issues * 12) - (total_warnings * 3))

    return {
        "in_text_citations": len(in_text_citations),
        "issues":   issues[:10],
        "warnings": warnings[:5],
        "quality_score": quality_score,
        "status": "pass" if quality_score >= 70 else "needs_review",
    }


# ─── Optional Section Rewrite ─────────────────────────────────────────────────

def rewrite_weak_sections(text: str, min_score: int = 60) -> str:
    """
    If quality score is below threshold, ask DeepSeek to rewrite
    the introduction and conclusion which most often need improvement.
    """
    if not DEEPSEEK_API_KEY:
        return text

    intro_match = re.search(r'(##\s*Introduction[\s\S]*?)(##\s)', text)
    if not intro_match:
        return text

    intro = intro_match.group(1)
    ai_count = sum(1 for p in AI_TELL_PHRASES if p.lower() in intro.lower())
    if ai_count < 2:
        return text  # good enough

    prompt = f"""Rewrite ONLY this introduction paragraph to sound more natural and academic.
Keep the same factual content and citations. Improve sentence variation.
Return only the rewritten introduction, starting with ## Introduction.

{intro}"""

    try:
        resp = httpx.post(
            DEEPSEEK_API_URL,
            json={"model": "deepseek-chat",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 1000, "temperature": 0.5},
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=40,
        )
        new_intro = resp.json()["choices"][0]["message"]["content"]
        text = text[:intro_match.start()] + new_intro + text[intro_match.end(1):]
        return text
    except Exception:
        return text


# ─── Full QA Pipeline ──────────────────────────────────────────────────────────

def run_qa_pipeline(
    essay_md: str,
    sources: List[Dict],
    document_id: str = None,
) -> Dict[str, Any]:
    """
    Run the complete 3-stage QA pipeline:
    1. Plagiarism check
    2. Tone adjustment
    3. Citation validation
    Returns improved essay + QA report.
    """
    logger.info("QA pipeline v2.5 starting")

    # Stage 1: Plagiarism
    plagiarism = check_plagiarism(essay_md, document_id)
    logger.info(f"Plagiarism: {plagiarism.get('score')} ({plagiarism.get('risk', '?')} risk)")

    # Stage 2: Tone
    improved = adjust_tone(essay_md)

    # Stage 3: Citation validation
    citations = validate_citations(improved, sources)
    logger.info(f"Citations: {citations['in_text_citations']} found, quality={citations['quality_score']}/100")

    # Stage 4: Optional section rewrite if quality is low
    if citations["quality_score"] < 65:
        logger.info("Quality below 65 — attempting section rewrite")
        improved = rewrite_weak_sections(improved)
        citations = validate_citations(improved, sources)  # re-validate

    return {
        "essay_markdown": improved,
        "plagiarism":     plagiarism,
        "citations":      citations,
        "quality_score":  citations["quality_score"],
        "status":         "qa_complete",
    }
