"""
Context Builder
Retrieves relevant chunks from vector store, groups by theme,
extracts key arguments and contradictions, and compiles the
writing context packet delivered to DeepSeek.
"""
import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def build_context(
    sources: List[Dict[str, Any]],
    analysis: Dict[str, Any],
    embeddings_available: bool = False,
    db=None,
) -> Dict[str, Any]:
    """
    Build a structured context packet for the writing agent.

    Args:
        sources:              normalised Paper objects
        analysis:             output of analyze_assignment()
        embeddings_available: whether pgvector search is usable
        db:                   SQLAlchemy session (optional, for vector search)

    Returns:
        Context dict with themes, key_papers, arguments, contradictions,
        methodologies, and formatted_sources.
    """
    if not sources:
        logger.warning("Context builder received empty sources — returning minimal context")
        return _empty_context(analysis)

    # ── 1. Group sources by theme/keyword match ──────────────────────────────
    keywords = [k.lower() for k in analysis.get("keywords", [])]
    sub_topics = [s.lower() for s in analysis.get("sub_topics", [])]

    theme_buckets: Dict[str, List[Dict]] = defaultdict(list)
    for paper in sources:
        title_lower = (paper.get("title") or "").lower()
        abstract_lower = (paper.get("abstract") or "").lower()
        text = title_lower + " " + abstract_lower

        matched = False
        for kw in keywords:
            if kw in text:
                theme_buckets[kw].append(paper)
                matched = True
                break
        if not matched:
            theme_buckets["general"].append(paper)

    # ── 2. Identify key papers (most cited / highest relevance) ──────────────
    def _score(paper: Dict) -> int:
        score = 0
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        topic_lower = analysis.get("topic", "").lower()

        if topic_lower[:20] in title:
            score += 10
        if paper.get("doi"):
            score += 5
        if paper.get("year") and int(paper.get("year", 0)) >= 2020:
            score += 3
        for kw in keywords[:4]:
            if kw in abstract:
                score += 2
        if paper.get("source_type") == "journal":
            score += 3
        return score

    ranked = sorted(sources, key=_score, reverse=True)
    key_papers = ranked[:15]

    # ── 3. Extract themes ─────────────────────────────────────────────────────
    themes = [kw for kw in keywords if theme_buckets.get(kw)] + sub_topics
    themes = list(dict.fromkeys(themes))[:6]

    # ── 4. Extract arguments from abstracts ──────────────────────────────────
    arguments = []
    for paper in key_papers[:10]:
        abstract = paper.get("abstract") or ""
        if len(abstract) > 80:
            # Take the first two sentences as the core argument
            sentences = abstract.replace("!", ".").replace("?", ".").split(". ")
            arg = ". ".join(sentences[:2]).strip()
            if arg:
                arguments.append(f"{paper.get('title','Unknown')} ({paper.get('year','n.d.')}): {arg}")

    # ── 5. Detect contradictions (papers with opposing keywords) ─────────────
    positive_kw = ["effective", "improves", "superior", "significant", "positive"]
    negative_kw = ["ineffective", "bias", "risk", "limitations", "challenges", "fails"]

    positive_papers = [
        p["title"] for p in key_papers
        if any(w in (p.get("abstract") or "").lower() for w in positive_kw)
    ]
    negative_papers = [
        p["title"] for p in key_papers
        if any(w in (p.get("abstract") or "").lower() for w in negative_kw)
    ]

    contradictions = []
    for i in range(min(2, len(positive_papers))):
        for j in range(min(2, len(negative_papers))):
            if positive_papers[i] != negative_papers[j]:
                contradictions.append(
                    f"{positive_papers[i]} (positive findings) vs {negative_papers[j]} (critical findings)"
                )

    # ── 6. Extract methodology list ──────────────────────────────────────────
    methodology_kw = [
        "regression", "meta-analysis", "systematic review", "qualitative",
        "quantitative", "survey", "case study", "experiment", "simulation",
        "machine learning", "deep learning", "interview", "longitudinal",
    ]
    methodologies_found = set()
    for paper in key_papers:
        text = (paper.get("abstract") or "").lower()
        for m in methodology_kw:
            if m in text:
                methodologies_found.add(m.title())

    # Add from analysis
    for m in analysis.get("methodology_types", []):
        methodologies_found.add(m.title())

    # ── 7. Format sources for the writing prompt ──────────────────────────────
    formatted_sources = []
    for p in key_papers:
        authors = p.get("authors") or []
        author_str = (
            authors[0].split(",")[0] if authors else "Unknown"
        ) + (" et al." if len(authors) > 2 else
              f" & {authors[1].split(',')[0]}" if len(authors) == 2 else "")

        formatted_sources.append({
            "citation_key": f"{author_str.split()[0]}{p.get('year', 'nd')}",
            "title": p.get("title", "Untitled"),
            "authors": authors,
            "year": p.get("year", "n.d."),
            "journal": p.get("journal", ""),
            "doi": p.get("doi", ""),
            "abstract": (p.get("abstract") or "")[:300],
            "citation_apa": p.get("citation_apa", ""),
            "access_method": p.get("access_method", "WEB_SOURCE"),
        })

    logger.info(
        f"Context built: {len(themes)} themes, {len(key_papers)} key papers, "
        f"{len(arguments)} arguments, {len(contradictions)} contradictions"
    )

    return {
        "themes": themes,
        "key_papers": formatted_sources,
        "arguments": arguments,
        "contradictions": contradictions[:4],
        "methodologies": list(methodologies_found)[:8],
        "formatted_sources": formatted_sources,
        "source_count": len(sources),
        "topic": analysis["topic"],
        "region_focus": analysis.get("region_focus", []),
        "required_sources": analysis.get("required_sources", 15),
    }


def _empty_context(analysis: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "themes": analysis.get("sub_topics", [analysis.get("topic", "")]),
        "key_papers": [],
        "arguments": [],
        "contradictions": [],
        "methodologies": analysis.get("methodology_types", []),
        "formatted_sources": [],
        "source_count": 0,
        "topic": analysis.get("topic", ""),
        "region_focus": analysis.get("region_focus", []),
        "required_sources": analysis.get("required_sources", 15),
    }
