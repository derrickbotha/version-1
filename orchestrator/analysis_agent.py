"""
Assignment Analysis Agent
Extracts research scope, keywords, methodology requirements,
and region focus from the assignment brief using DeepSeek.
"""
import httpx
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")


def analyze_assignment(
    title: str,
    topic: str,
    instructions: str,
    focus_area: Optional[str],
    word_count: int,
    academic_level: str,
    citation_style: str,
    module_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Use DeepSeek to extract a structured research plan from the assignment brief.

    Returns a dict with:
        topic, keywords, academic_level, required_sources,
        methodology_types, region_focus, citation_style,
        sub_topics, argument_angles, dataset_types
    """
    prompt = f"""You are an academic research analyst. Analyse the following assignment and extract a complete research plan.

ASSIGNMENT TITLE: {title}
MODULE: {module_code or 'Not specified'}
TOPIC: {topic}
INSTRUCTIONS: {instructions or 'None provided'}
SPECIFIC FOCUS: {focus_area or 'None specified'}
WORD COUNT: {word_count}
ACADEMIC LEVEL: {academic_level}
CITATION STYLE: {citation_style}

Extract and return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "topic": "<concise topic statement>",
  "keywords": ["<keyword1>", "<keyword2>", ..., "<keyword8>"],
  "academic_level": "{academic_level}",
  "required_sources": <int between 8 and 60 based on word count and level>,
  "methodology_types": ["<e.g. systematic review>", "<regression>", "<case study>"],
  "region_focus": ["<region or country, or 'Global' if none specified>"],
  "citation_style": "{citation_style}",
  "sub_topics": ["<sub-topic1>", "<sub-topic2>", "<sub-topic3>"],
  "argument_angles": ["<angle1>", "<angle2>", "<angle3>"],
  "dataset_types": ["<e.g. survey data>", "<longitudinal>"],
  "journal_domains": ["<domain1>", "<domain2>"],
  "key_authors_to_search": ["<potential author surname or institution>"],
  "time_range": "<e.g. 2018-2024>"
}}"""

    if DEEPSEEK_API_KEY:
        try:
            resp = httpx.post(
                DEEPSEEK_API_URL,
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.2,
                },
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Strip markdown code fences if present
            content = re.sub(r"```(?:json)?", "", content).strip().strip("`")
            return json.loads(content)
        except Exception as e:
            logger.warning(f"DeepSeek analysis failed ({e}), using heuristic fallback")

    return _heuristic_analysis(
        topic=topic,
        focus_area=focus_area,
        word_count=word_count,
        academic_level=academic_level,
        citation_style=citation_style,
    )


def _heuristic_analysis(
    topic: str,
    focus_area: Optional[str],
    word_count: int,
    academic_level: str,
    citation_style: str,
) -> Dict[str, Any]:
    """Rule-based fallback analysis when DeepSeek is unavailable."""
    words = (topic + " " + (focus_area or "")).lower().split()
    keywords = list(dict.fromkeys(w for w in words if len(w) > 4))[:8]

    source_map = {
        "high_school": 8,
        "undergraduate": 15,
        "postgraduate": 25,
        "phd": 50,
    }
    required_sources = max(
        source_map.get(academic_level, 15),
        word_count // 200,
    )

    return {
        "topic": topic,
        "keywords": keywords or [topic],
        "academic_level": academic_level,
        "required_sources": required_sources,
        "methodology_types": ["literature review"],
        "region_focus": ["Global"],
        "citation_style": citation_style,
        "sub_topics": [topic],
        "argument_angles": [f"Critical analysis of {topic}"],
        "dataset_types": ["secondary data"],
        "journal_domains": ["multidisciplinary"],
        "key_authors_to_search": [],
        "time_range": "2018-2024",
    }
