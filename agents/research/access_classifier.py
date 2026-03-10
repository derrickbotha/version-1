"""
Access Intelligence Classifier
Determines how each paper can be accessed and stores the classification.

Access methods:
    OPEN_ACCESS    — Free, no login required (PubMed, arXiv, DOAJ, etc.)
    INSTITUTIONAL  — Requires university library login
    PROXY          — Available via EZproxy / VPN
    MEMBERSHIP     — Requires paid membership (ACM, IEEE without key)
    AUTHOR_COPY    — PDF available from author's personal/institutional page
    WEB_SOURCE     — Found on open web, access uncertain
"""
import logging
import re
from typing import Dict, List, Any, Optional
from .normalizer import lookup_doi_crossref

logger = logging.getLogger(__name__)

# Open-access domains/patterns
OA_DOMAINS = [
    "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov",
    "doaj.org", "core.ac.uk", "openalex.org", "semanticscholar.org",
    "europepmc.org", "unpaywall.org", "biorxiv.org", "medrxiv.org",
    "ssrn.com", "researchgate.net", "academia.edu", "zenodo.org",
]

# Institutional/paid domains
INSTITUTIONAL_DOMAINS = [
    "sciencedirect.com", "scopus.com", "elsevier.com",
    "springer.com", "springerlink.com", "link.springer.com",
    "wiley.com", "onlinelibrary.wiley.com",
    "jstor.org", "oxford.ac.uk", "oup.com", "academic.oup.com",
    "tandfonline.com", "sage.com", "sagepub.com",
    "ieee.org", "ieeexplore.ieee.org",
    "acm.org", "dl.acm.org",
    "proquest.com", "ebsco.com",
]

# Author copy patterns
AUTHOR_COPY_PATTERNS = [
    r'academia\.edu',
    r'researchgate\.net',
    r'\.edu/.*\.pdf',
    r'\.ac\.uk/.*\.pdf',
    r'github\.com',
    r'hal\.archives-ouvertes\.fr',
]


def classify_access(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Classify access method for each paper.
    Also attempts CrossRef DOI lookup for papers missing DOIs.
    """
    for paper in papers:
        paper["access_method"] = _classify_single(paper)

        # Attempt DOI resolution for papers without DOIs
        if not paper.get("doi") and paper.get("title"):
            doi = lookup_doi_crossref(paper["title"], paper.get("authors", []))
            if doi:
                paper["doi"] = doi
                if not paper.get("url"):
                    paper["url"] = f"https://doi.org/{doi}"
                logger.debug(f"DOI resolved via CrossRef: {doi}")

    # Summary stats
    counts: Dict[str, int] = {}
    for p in papers:
        m = p.get("access_method", "UNKNOWN")
        counts[m] = counts.get(m, 0) + 1

    logger.info(f"Access classification: {counts}")
    return papers


def _classify_single(paper: Dict[str, Any]) -> str:
    """Determine the access method for one paper."""
    existing = paper.get("access_method")

    # Trust agent-assigned OPEN_ACCESS from arXiv/DOAJ/CrossRef
    if existing in ("OPEN_ACCESS",) and paper.get("_source_agent") in (
        "arxiv", "doaj", "crossref", "crossref_inst",
    ):
        return "OPEN_ACCESS"

    url   = (paper.get("url") or "").lower()
    doi   = (paper.get("doi") or "").lower()
    agent = paper.get("_source_agent", "")

    # ── Rule 1: OA by domain ──────────────────────────────────────────────
    for domain in OA_DOMAINS:
        if domain in url:
            return "OPEN_ACCESS"

    # ── Rule 2: Author copy patterns ──────────────────────────────────────
    for pattern in AUTHOR_COPY_PATTERNS:
        if re.search(pattern, url):
            return "AUTHOR_COPY"

    # ── Rule 3: Institutional domain ─────────────────────────────────────
    for domain in INSTITUTIONAL_DOMAINS:
        if domain in url:
            return "INSTITUTIONAL"

    # ── Rule 4: Source agent implies institutional ─────────────────────────
    if agent in ("scopus", "springer", "ieee", "crossref_inst"):
        return "INSTITUTIONAL"

    # ── Rule 5: Known OA publishers via DOI prefix ────────────────────────
    # PLoS: 10.1371, MDPI: 10.3390, Hindawi: 10.1155, BioMed Central: 10.1186
    oa_doi_prefixes = ["10.1371/", "10.3390/", "10.1155/", "10.1186/", "10.48550/"]
    for prefix in oa_doi_prefixes:
        if doi.startswith(prefix):
            return "OPEN_ACCESS"

    # ── Rule 6: Perplexity-sourced — likely web findable ──────────────────
    if agent == "perplexity":
        return "WEB_SOURCE"

    # ── Rule 7: Has DOI but no matching domain → proxy-accessible ─────────
    if doi:
        return "PROXY"

    return "WEB_SOURCE"
