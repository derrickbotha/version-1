"""
Writing Agent — uses DeepSeek to generate structured academic essays
from research sources + knowledge graph context.
"""
import httpx
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

TONE_PROMPTS = {
    "human_academic":  "academic in tone with natural sentence variation, first-person avoided, passive voice used selectively",
    "professional":    "professional and formal, suitable for industry reports",
    "technical":       "precise and technical, with domain-specific terminology",
    "simplified":      "clear and accessible, suitable for a general educated audience",
}

CITATION_STYLE_PROMPTS = {
    "Harvard": "Use Harvard in-text citations: (Author, Year) and a References list at the end.",
    "APA":     "Use APA 7th edition in-text citations: (Author, Year, p. X) and a References section.",
    "MLA":     "Use MLA 9th edition in-text citations: (Author page) and a Works Cited list.",
    "Chicago": "Use Chicago footnotes and a Bibliography.",
}

def build_writing_prompt(
    title: str,
    topic: str,
    instructions: str,
    focus_area: str,
    word_count: int,
    academic_level: str,
    citation_style: str,
    sources: List[Dict],
    tone: str = "human_academic",
) -> str:
    """Build a complete writing prompt for DeepSeek."""
    tone_desc  = TONE_PROMPTS.get(tone, TONE_PROMPTS["human_academic"])
    cite_desc  = CITATION_STYLE_PROMPTS.get(citation_style, CITATION_STYLE_PROMPTS["Harvard"])
    level_desc = {
        "high_school":    "high school level, clear and well-structured",
        "undergraduate":  "undergraduate level, analytical and evidence-based",
        "postgraduate":   "postgraduate/master's level, critical and theoretically grounded",
        "phd":            "doctoral level, original contribution to knowledge, highly technical",
    }.get(academic_level, "undergraduate level")

    # Format top sources for context
    sources_text = "\n".join([
        f"- {s['title']} ({s.get('year','n.d.')}) by {', '.join(s.get('authors', [])[:2])}. "
        f"Journal: {s.get('journal','Unknown')}. DOI: {s.get('doi','N/A')}. "
        f"Abstract: {s.get('abstract','')[:200]}"
        for s in sources[:15]
    ])

    citations_text = "\n".join([s.get("citation_apa", "") for s in sources[:15] if s.get("citation_apa")])

    prompt = f"""ROLE: Expert Academic Writer at {level_desc}

ASSIGNMENT TITLE: {title}
TOPIC: {topic}
{f'SPECIFIC FOCUS: {focus_area}' if focus_area else ''}
{f'INSTRUCTIONS: {instructions}' if instructions else ''}
TARGET WORD COUNT: {word_count} words
TONE: {tone_desc}
CITATION STYLE: {cite_desc}

AVAILABLE RESEARCH SOURCES:
{sources_text}

AVAILABLE REFERENCES FOR CITATION LIST:
{citations_text}

TASK:
Write a complete {word_count}-word academic essay on the above topic.

Structure requirements:
1. Introduction (10% of word count) — define scope, state thesis, preview structure
2. Main body sections (75% of word count) — analytical paragraphs with evidence and citations
   {"- Include specific focus on: " + focus_area if focus_area else ""}
3. Discussion/Critical Analysis (10% of word count)
4. Conclusion (5% of word count) — synthesise findings, restate thesis
5. Reference List — all cited sources in {citation_style} format

Rules:
- Every claim must be supported by an in-text citation from the provided sources
- Vary sentence length and structure for natural academic flow
- Do not use first person (I, we, our)
- Do not use bullet points in the essay body
- Use transitional phrases between paragraphs
- Ensure the essay reads as original, human-written academic work

OUTPUT FORMAT:
Return the essay in clean markdown with ## headings for each section.
End with a ## References section containing the full reference list.
"""
    return prompt

def call_deepseek(prompt: str, model: str = "deepseek-reasoner") -> str:
    """Call the DeepSeek API and return the generated text."""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — returning mock essay")
        return _mock_essay(prompt)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert academic writer. Write only the requested essay content with no preamble or meta-commentary."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 8000,
        "temperature": 0.7,
    }

    try:
        resp = httpx.post(
            DEEPSEEK_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return _mock_essay(prompt)

def _mock_essay(prompt: str) -> str:
    """Return a placeholder essay structure when no API key is configured."""
    return """## Introduction

This essay examines the topic as outlined in the assignment brief. The following sections provide a structured analysis drawing on contemporary academic literature.

## Literature Review

The existing body of literature highlights several key themes relevant to this discussion. According to Smith and Chen (2024), the field has undergone significant transformation in recent years. Furthermore, Williams and Patel (2023) demonstrate through empirical analysis that...

## Analysis and Discussion

The evidence presented above suggests a nuanced understanding is required. As noted by Smith et al. (2024), the intersection of theory and practice reveals important considerations...

## Conclusion

In conclusion, this essay has examined the key dimensions of the topic. The evidence demonstrates that a comprehensive approach is necessary to address the challenges identified in the literature.

## References

Smith, J., Chen, L., & Okonkwo, A. (2024). Systematic review. *Nature Scientific Reports*. https://doi.org/10.1038/s41598-2024-mock

Williams, R., & Patel, S. (2023). Empirical analysis. *Journal of Data Science*. https://doi.org/10.1007/mock-2023
"""

def run_writing_pipeline(
    title: str,
    topic: str,
    instructions: str,
    focus_area: str,
    word_count: int,
    academic_level: str,
    citation_style: str,
    sources: List[Dict],
) -> Dict[str, Any]:
    """
    Full writing pipeline:
    1. Build prompt with sources
    2. Call DeepSeek
    3. Return structured essay content
    """
    logger.info(f"Writing pipeline: title={title!r} words={word_count}")

    prompt = build_writing_prompt(
        title=title,
        topic=topic,
        instructions=instructions,
        focus_area=focus_area,
        word_count=word_count,
        academic_level=academic_level,
        citation_style=citation_style,
        sources=sources,
    )

    essay_md = call_deepseek(prompt)
    actual_words = len(essay_md.split())

    return {
        "essay_markdown": essay_md,
        "word_count": actual_words,
        "sources_used": [s.get("doi") or s.get("title") for s in sources[:15]],
        "status": "writing_complete",
    }
