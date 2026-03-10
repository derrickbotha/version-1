"""
Source Normalizer & DOI Extractor
Standardises all papers from different agents into a uniform Paper object.
Extracts DOIs from URLs, text patterns, and CrossRef lookup fallback.
"""
import re
import logging
import os
from typing import Dict, List, Any, Optional
import httpx

logger = logging.getLogger(__name__)

CROSSREF_API = "https://api.crossref.org/works"
DOI_PATTERN  = re.compile(r'\b(10\.\d{4,}(?:\.\d+)*/\S+)\b')


def normalize_sources(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize all papers to a standard Paper object format.
    Extracts DOIs, cleans authors, standardises year to int.

    Paper object structure:
    {
        "title": str,
        "authors": [str],
        "year": int | None,
        "journal": str,
        "doi": str | None,
        "url": str | None,
        "abstract": str,
        "source_type": str,       # journal | preprint | gov | dataset | OA
        "pdf_path": str | None,
        "access_method": str,     # OPEN_ACCESS | INSTITUTIONAL | WEB_SOURCE | etc.
        "citation_apa": str,
        "citation_count": int,
        "_source_agent": str,
        "_normalized": True
    }
    """
    normalized = []
    seen_titles: set = set()

    for raw in papers:
        try:
            paper = _normalize_single(raw)

            # Deduplicate by title (case-insensitive)
            title_key = paper["title"].lower().strip()[:80]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            normalized.append(paper)
        except Exception as e:
            logger.warning(f"Failed to normalize paper: {e} — {str(raw)[:100]}")

    logger.info(f"Normalized {len(normalized)} papers from {len(papers)} raw")
    return normalized


def _normalize_single(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one raw paper dict."""
    # ── Title ───────────────────────────────────────────────────────────────
    title = (raw.get("title") or "Untitled").strip()
    if isinstance(title, list):
        title = title[0]
    title = re.sub(r'\s+', ' ', title)

    # ── Authors ─────────────────────────────────────────────────────────────
    authors = raw.get("authors") or []
    if isinstance(authors, str):
        authors = [a.strip() for a in re.split(r'[,;]', authors) if a.strip()]
    authors = [str(a).strip() for a in authors if a][:20]

    # ── Year ────────────────────────────────────────────────────────────────
    year = raw.get("year")
    if year is not None:
        try:
            year = int(str(year)[:4])
        except (ValueError, TypeError):
            year = None

    # ── Journal ─────────────────────────────────────────────────────────────
    journal = (raw.get("journal") or raw.get("source") or "").strip()

    # ── DOI extraction ───────────────────────────────────────────────────────
    doi = _extract_doi(raw)

    # ── URL ─────────────────────────────────────────────────────────────────
    url = raw.get("url") or raw.get("link")
    if doi and not url:
        url = f"https://doi.org/{doi}"

    # ── Abstract ────────────────────────────────────────────────────────────
    abstract = (raw.get("abstract") or "").strip()[:600]
    # Strip HTML tags if present
    abstract = re.sub(r'<[^>]+>', '', abstract)
    abstract = re.sub(r'&\w+;', ' ', abstract).strip()

    # ── Source type ──────────────────────────────────────────────────────────
    source_type = raw.get("source_type", "journal")
    if "arxiv" in (url or "").lower():
        source_type = "preprint"
    elif "gov" in (url or "").lower() or "parliament" in (url or "").lower():
        source_type = "gov"
    elif "dataset" in title.lower() or "data" in source_type:
        source_type = "dataset"

    # ── APA Citation ─────────────────────────────────────────────────────────
    citation_apa = raw.get("citation_apa") or _format_apa(authors, year, title, journal, doi)

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "url": url,
        "abstract": abstract,
        "source_type": source_type,
        "pdf_path": raw.get("pdf_path"),
        "access_method": raw.get("access_method", "WEB_SOURCE"),
        "citation_apa": citation_apa,
        "citation_count": raw.get("citation_count", 0),
        "_source_agent": raw.get("_source_agent", "unknown"),
        "_normalized": True,
    }


def _extract_doi(raw: Dict[str, Any]) -> Optional[str]:
    """
    Multi-strategy DOI extraction:
    1. Direct doi field
    2. URL pattern (doi.org/10.xxxx/...)
    3. Regex in url/link fields
    4. Returns None if not found (CrossRef lookup is done in access_classifier)
    """
    # Strategy 1: direct field
    doi = raw.get("doi")
    if doi:
        doi = str(doi).strip().lstrip("https://doi.org/").lstrip("http://dx.doi.org/")
        if DOI_PATTERN.search(doi):
            return doi
        match = DOI_PATTERN.search(doi)
        if match:
            return match.group(1)

    # Strategy 2: from URL
    for field in ["url", "link", "html_url"]:
        url = raw.get(field, "")
        if url and "doi.org/" in url:
            parts = url.split("doi.org/")
            if len(parts) > 1:
                candidate = parts[1].split("?")[0].split("#")[0].strip()
                if DOI_PATTERN.search(candidate):
                    return candidate

    # Strategy 3: regex in any text field
    for field in ["abstract", "title"]:
        text = raw.get(field, "")
        if text:
            match = DOI_PATTERN.search(str(text))
            if match:
                return match.group(1)

    return None


def _format_apa(authors: List[str], year: Optional[int], title: str,
                journal: str, doi: Optional[str]) -> str:
    """Format an APA 7th edition citation."""
    if not authors:
        author_str = "Unknown Author"
    elif len(authors) == 1:
        author_str = authors[0]
    elif len(authors) <= 20:
        author_str = ", ".join(authors[:-1]) + f", & {authors[-1]}"
    else:
        author_str = ", ".join(authors[:19]) + ", ... " + authors[-1]

    yr = f"({year})" if year else "(n.d.)"
    citation = f"{author_str} {yr}. {title}."
    if journal:
        citation += f" *{journal}*."
    if doi:
        citation += f" https://doi.org/{doi}"
    return citation


def lookup_doi_crossref(title: str, authors: List[str]) -> Optional[str]:
    """Synchronous CrossRef DOI lookup by title + first author."""
    try:
        query = title
        if authors:
            last_name = authors[0].split(",")[0].strip()
            query = f"{query} {last_name}"

        resp = httpx.get(
            CROSSREF_API,
            params={
                "query": query,
                "rows": 1,
                "select": "DOI,title",
                "mailto": "asa@scholarassistant.ai",
            },
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        if items:
            return items[0].get("DOI")
    except Exception as e:
        logger.debug(f"CrossRef DOI lookup failed for '{title[:40]}': {e}")
    return None
