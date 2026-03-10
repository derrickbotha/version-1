"""
Writing Agent v2.5 — Context-Aware Academic Essay Generator
Uses DeepSeek deepseek-reasoner with the full Context Builder output:
- themes, key_papers, arguments, contradictions, methodologies
- Focus area, region focus, academic level
- APA/Harvard/MLA/Chicago citation styles
"""
import httpx
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

TONE_PROMPTS = {
    "human_academic":  "natural, varied-sentence academic prose — avoid bullet points in body paragraphs",
    "professional":    "formal professional register suitable for industry or policy reports",
    "technical":       "precise and technical with domain-specific terminology and quantitative rigour",
    "simplified":      "clear, accessible language for a general educated readership",
}

CITATION_STYLE_FORMATS = {
    "Harvard": "Harvard (Author, Year) in-text; References list at end",
    "APA":     "APA 7th edition (Author, Year, p. X); References section",
    "MLA":     "MLA 9th edition (Author Page); Works Cited list",
    "Chicago": "Chicago footnotes; Bibliography",
}

LEVEL_EXPECTATIONS = {
    "high_school":   "Clear argument, basic evidence, 3–5 sources, accessible language",
    "undergraduate": "Analytical paragraphs, 10–15 sources, topic sentences, critical engagement with literature",
    "postgraduate":  "Theoretically grounded, 20+ sources, identifies research gaps, contradictions addressed, original synthesis",
    "phd":           "Original contribution, 40+ sources, epistemological positioning, rigorous methodology critique, engagement with primary data",
}


def build_writing_prompt(
    title: str,
    topic: str,
    instructions: str,
    focus_area: Optional[str],
    word_count: int,
    academic_level: str,
    citation_style: str,
    context: Dict[str, Any],
) -> str:
    """Build a comprehensive writing prompt using the full context."""
    sources        = context.get("formatted_sources", [])
    themes         = context.get("themes", [])
    arguments      = context.get("arguments", [])
    contradictions = context.get("contradictions", [])
    methodologies  = context.get("methodologies", [])
    region_focus   = context.get("region_focus", [])

    tone_desc  = TONE_PROMPTS.get("human_academic")
    cite_desc  = CITATION_STYLE_FORMATS.get(citation_style, CITATION_STYLE_FORMATS["Harvard"])
    level_desc = LEVEL_EXPECTATIONS.get(academic_level, LEVEL_EXPECTATIONS["undergraduate"])

    # Format sources block (top 20)
    sources_block = "\n".join([
        f"• [{s.get('citation_key','?')}] {s.get('title','?')[:80]} "
        f"({s.get('year','n.d.')}) — {s.get('journal','')[:40]} — "
        f"DOI: {s.get('doi') or 'N/A'} — "
        f"Abstract: {s.get('abstract','')[:150]}"
        for s in sources[:20]
    ])

    # Format references block
    references_block = "\n".join([
        s.get("citation_apa", s.get("title", ""))
        for s in sources[:20]
        if s.get("citation_apa") or s.get("title")
    ])

    # Arguments + contradictions for analytical depth
    args_block = "\n".join([f"- {a}" for a in arguments[:8]])
    cont_block = "\n".join([f"- {c}" for c in contradictions[:4]])

    region_str = ", ".join(region_focus) if region_focus and region_focus[0].lower() != "global" else ""

    prompt = f"""ROLE: Expert Academic Writer — {academic_level.replace('_', ' ').title()} Level

ASSIGNMENT TITLE: {title}
TOPIC: {topic}
{"SPECIFIC FOCUS: " + focus_area if focus_area else ""}
{"REGIONAL SCOPE: " + region_str if region_str else ""}
TARGET WORD COUNT: {word_count} words (±5%)
ACADEMIC LEVEL EXPECTATIONS: {level_desc}
CITATION STYLE: {cite_desc}
PROSE TONE: {tone_desc}

RESEARCH THEMES IDENTIFIED:
{chr(10).join(f"• {t}" for t in themes[:6])}

METHODOLOGIES FOUND IN LITERATURE:
{chr(10).join(f"• {m}" for m in methodologies[:6])}

KEY ARGUMENTS FROM LITERATURE:
{args_block or "None extracted — use your reasoning"}

CONTRADICTIONS / DEBATES IN LITERATURE:
{cont_block or "None identified"}

AVAILABLE RESEARCH SOURCES (use these for all citations):
{sources_block or "No sources available — use general knowledge"}

REFERENCE LIST (use exactly for the References section):
{references_block or "No references available"}

{f"ADDITIONAL INSTRUCTIONS: {instructions}" if instructions else ""}

═══════════════════════════════════════════════════════════════
TASK: Write a complete {word_count}-word academic essay.

REQUIRED STRUCTURE:
## Introduction ({int(word_count * 0.10)} words)
- Define the topic and its significance
- State the thesis / research question
- Outline the essay structure
- Include at least 2 in-text citations

## Literature Review ({int(word_count * 0.25)} words)
- Critically synthesise the identified themes
- Compare and contrast key authors
- {"Address contradictions and debates: " + cont_block[:200] if cont_block else "Identify gaps in existing research"}
- Minimum 5 in-text citations from the sources list

## Analysis / Discussion ({int(word_count * 0.35)} words)
- Apply the literature to the specific focus: {focus_area or topic}
{"- Include " + region_str + "-specific examples and case studies" if region_str else ""}
- Engage with methodologies: {", ".join(methodologies[:3]) if methodologies else "appropriate methods"}
- Minimum 5 in-text citations

## Critical Evaluation ({int(word_count * 0.15)} words)
- Assess strengths and limitations of the evidence
- Note research gaps and future directions
- Maintain a balanced, evidence-based argument

## Conclusion ({int(word_count * 0.10)} words)
- Synthesise key findings
- Restate thesis in light of the evidence
- Recommend implications for practice / policy
- NO new citations in conclusion

## References
- FULL reference list in {citation_style} format
- Include every source cited in the essay
- Alphabetical order

═══════════════════════════════════════════════════════════════
WRITING RULES:
1. Every factual claim must have an in-text citation
2. Use (Author, Year) format — never footnote numbers
3. Vary sentence length: mix short (8–12 words), medium (20–25 words), long (30+ words)
4. NO first person (I, we, our) unless quoting
5. NO bullet points in body paragraphs — prose only
6. NO AI-typical openers ("In today's world", "It is important to note", "In conclusion, it is clear that")
7. Use academic connectors: "Moreover,", "Conversely,", "Building on this,", "A notable exception is..."
8. Return ONLY the essay in clean markdown. No preamble, no meta-commentary."""

    return prompt


def call_deepseek(prompt: str, word_count: int) -> str:
    """Call DeepSeek API and return generated essay."""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — returning mock essay")
        return _mock_essay()

    # Scale tokens with word count
    max_tokens = min(max(word_count * 2, 2000), 8000)

    try:
        resp = httpx.post(
            DEEPSEEK_API_URL,
            json={
                "model": "deepseek-reasoner",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert academic writer. Write the requested essay exactly as specified. Return only the essay content in markdown format.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.65,
            },
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            timeout=150,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek writing error: {e}")
        return _mock_essay()


def _mock_essay() -> str:
    return """## Introduction

This essay examines the assigned topic through a critical lens, drawing on contemporary peer-reviewed literature. The central thesis posits that a comprehensive, evidence-based approach is necessary to address the complexities inherent in this field. The essay proceeds as follows: first, relevant literature is reviewed; second, a detailed analysis is presented; third, a critical evaluation is offered before conclusions are drawn.

## Literature Review

The scholarly literature on this subject has expanded considerably in recent years. Smith and Chen (2024) argue that foundational frameworks must be revisited in light of emerging empirical evidence. Their systematic review of 47 studies demonstrates a consistent pattern across diverse institutional contexts. Conversely, Williams and Patel (2023) identify significant limitations in this approach, noting that methodological heterogeneity compromises comparability across studies.

Building on these foundations, the field has increasingly turned towards mixed-methods approaches. Johnson et al. (2022) demonstrate through a longitudinal study spanning five years that such approaches yield more nuanced insights than single-methodology designs.

## Analysis

The analysis presented herein synthesises the key themes identified in the literature. The evidence consistently supports the proposition that contextual factors play a decisive role in shaping outcomes. Moreover, the regional dimensions of this phenomenon cannot be overstated.

## Critical Evaluation

The body of evidence reviewed presents notable strengths. The breadth of methodological approaches employed across the cited studies lends robustness to the overall findings. However, several limitations warrant acknowledgement.

## Conclusion

This essay has examined the key dimensions of the assigned topic through a systematic review of the available evidence. The analysis demonstrates that a nuanced, context-sensitive approach is essential for both research and practice.

## References

Smith, J., Chen, L., & Okonkwo, A. (2024). Systematic review of current approaches. *Nature Scientific Reports*, 14(1), 1–18. https://doi.org/10.1038/s41598-2024-mock

Williams, R., & Patel, S. (2023). Methodological considerations. *Journal of Data Science*, 12(3), 45–62. https://doi.org/10.1007/mock-2023
"""


def run_writing_pipeline(
    title: str,
    topic: str,
    instructions: str,
    focus_area: Optional[str],
    word_count: int,
    academic_level: str,
    citation_style: str,
    sources: List[Dict],
    context: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Full writing pipeline with context integration."""
    logger.info(f"Writing pipeline: '{title[:50]}' | {word_count} words | {academic_level}")

    ctx = context or {
        "formatted_sources": sources,
        "themes": [],
        "arguments": [],
        "contradictions": [],
        "methodologies": [],
        "region_focus": [],
    }

    prompt   = build_writing_prompt(title, topic, instructions, focus_area,
                                     word_count, academic_level, citation_style, ctx)
    essay_md = call_deepseek(prompt, word_count)
    word_cnt = len(essay_md.split())

    return {
        "essay_markdown": essay_md,
        "word_count": word_cnt,
        "sources_used": [s.get("doi") or s.get("title") for s in sources[:20]],
        "status": "writing_complete",
    }
