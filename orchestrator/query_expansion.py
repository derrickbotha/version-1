"""
Query Expansion Engine
Generates multiple search query variations to maximise research coverage.
Produces queries for: keyword search, author search, journal search, dataset search.
"""
import logging
import os
import re
import json
from typing import Dict, List, Any
import httpx

logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")


def expand_queries(analysis: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Generate comprehensive query sets from the analysis result.

    Returns:
        {
          "keyword_queries": [...],   # for database full-text search
          "author_queries": [...],    # targeted author searches
          "journal_queries": [...],   # specific journal scans
          "dataset_queries": [...],   # dataset repository searches
          "oa_queries": [...],        # open access optimised queries
          "boolean_queries": [...],   # advanced boolean for Scopus/WoS
        }
    """
    topic = analysis["topic"]
    keywords = analysis["keywords"]
    region_focus = analysis.get("region_focus", ["Global"])
    methodology_types = analysis.get("methodology_types", [])
    journal_domains = analysis.get("journal_domains", [])
    authors = analysis.get("key_authors_to_search", [])
    time_range = analysis.get("time_range", "2018-2024")
    sub_topics = analysis.get("sub_topics", [])

    # ── Keyword queries ───────────────────────────────────────────────────────
    keyword_queries = [topic]

    # Combine keywords in pairs
    for i in range(0, min(len(keywords), 6), 2):
        pair = " ".join(keywords[i:i+2])
        keyword_queries.append(pair)

    # Add sub-topic queries
    keyword_queries.extend(sub_topics[:3])

    # Add region-scoped queries
    for region in region_focus[:2]:
        if region.lower() != "global":
            keyword_queries.append(f"{topic} {region}")

    # Add methodology-scoped queries
    for method in methodology_types[:2]:
        keyword_queries.append(f"{topic} {method}")

    # ── Boolean queries (Scopus/WoS/IEEE format) ──────────────────────────────
    kw_or = " OR ".join(f'"{k}"' for k in keywords[:5])
    boolean_queries = [
        f'TITLE-ABS-KEY({kw_or}) AND PUBYEAR > {time_range.split("-")[0]}',
        f'TITLE-ABS-KEY("{topic}") AND DOCTYPE(ar)',
    ]
    if region_focus and region_focus[0].lower() != "global":
        boolean_queries.append(
            f'TITLE-ABS-KEY({kw_or}) AND AFFILCOUNTRY("{region_focus[0]}")'
        )

    # ── Author queries ────────────────────────────────────────────────────────
    author_queries = [f"author:{a}" for a in authors[:5]] if authors else []

    # ── Journal queries ───────────────────────────────────────────────────────
    journal_queries = [f'source:"{jd}"' for jd in journal_domains[:4]] if journal_domains else []

    # ── Dataset queries ───────────────────────────────────────────────────────
    dataset_types = analysis.get("dataset_types", [])
    dataset_queries = [f"{topic} dataset {dt}" for dt in dataset_types[:3]]
    dataset_queries.append(f"{topic} open data")

    # ── OA-optimised queries ──────────────────────────────────────────────────
    oa_queries = [
        f"{topic} site:arxiv.org",
        f"{topic} filetype:pdf",
        f"{topic} open access preprint",
    ]
    for k in keywords[:3]:
        oa_queries.append(f"{k} research {time_range.split('-')[1] or '2024'}")

    logger.info(
        f"Expanded to {len(keyword_queries)} keyword + {len(boolean_queries)} boolean queries"
    )

    return {
        "keyword_queries": list(dict.fromkeys(keyword_queries)),
        "author_queries": author_queries,
        "journal_queries": journal_queries,
        "dataset_queries": dataset_queries,
        "oa_queries": oa_queries,
        "boolean_queries": boolean_queries,
        "all_queries": list(dict.fromkeys(keyword_queries + oa_queries)),
    }
