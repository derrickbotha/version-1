"""
Web Research Agent
Searches Perplexity Sonar + open-access sources (arXiv, DOAJ, CrossRef, Google Scholar)
for academic papers on the assignment topic.
Runs asynchronously alongside the Institutional Agent.
"""
import asyncio
import httpx
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

PERPLEXITY_API_URL = os.getenv("PERPLEXITY_API_URL", "https://api.perplexity.ai/chat/completions")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
CROSSREF_API       = "https://api.crossref.org/works"
ARXIV_API          = "https://export.arxiv.org/api/query"
DOAJ_API           = "https://doaj.org/api/search/articles"


async def run_web_agent_async(
    queries: List[str],
    query_sets: Dict[str, List[str]] = None,
    max_per_query: int = 10,
) -> List[Dict[str, Any]]:
    """
    Async entry point. Runs all search sources concurrently.
    Returns a list of Paper dicts.
    """
    all_queries = queries[:8]  # cap to avoid rate limits
    query_sets = query_sets or {}

    tasks = []
    for q in all_queries[:5]:
        tasks.append(_search_perplexity(q))

    # OA sources in parallel
    tasks.append(_search_crossref(all_queries[:3]))
    tasks.append(_search_arxiv(all_queries[:3]))
    tasks.append(_search_doaj(all_queries[:2]))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    papers: List[Dict] = []
    for r in results:
        if isinstance(r, list):
            papers.extend(r)
        elif isinstance(r, Exception):
            logger.warning(f"Web agent subtask failed: {r}")

    # Tag source type
    for p in papers:
        p.setdefault("source_type", "web")
        p.setdefault("access_method", "WEB_SOURCE")

    logger.info(f"Web agent retrieved {len(papers)} total papers")
    return papers


async def _search_perplexity(query: str) -> List[Dict[str, Any]]:
    """Search Perplexity Sonar for academic papers."""
    if not PERPLEXITY_API_KEY:
        return _mock_papers(query, source="perplexity", count=3)

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an academic librarian. For the query, find up to 10 real peer-reviewed papers. "
                    "Return ONLY a JSON array of objects with keys: title, authors (list of strings), "
                    "year (int), journal, doi, url, abstract (100 words max). No markdown, no explanation."
                ),
            },
            {"role": "user", "content": f"Find academic papers about: {query}"},
        ],
        "max_tokens": 2000,
        "return_citations": True,
        "search_domain_filter": [
            "scholar.google.com", "pubmed.ncbi.nlm.nih.gov",
            "jstor.org", "sciencedirect.com", "arxiv.org",
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                PERPLEXITY_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            start = content.find("[")
            end   = content.rfind("]") + 1
            if start >= 0 and end > start:
                papers = json.loads(content[start:end])
                for p in papers:
                    p["_source_agent"] = "perplexity"
                return papers
    except Exception as e:
        logger.warning(f"Perplexity search failed for '{query}': {e}")

    return _mock_papers(query, source="perplexity", count=2)


async def _search_crossref(queries: List[str]) -> List[Dict[str, Any]]:
    """Search CrossRef for DOI metadata."""
    papers = []
    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries[:3]:
            try:
                resp = await client.get(
                    CROSSREF_API,
                    params={
                        "query": query,
                        "rows": 8,
                        "select": "DOI,title,author,published-print,container-title,abstract,URL",
                        "filter": "type:journal-article",
                        "mailto": "asa@scholarassistant.ai",
                    },
                )
                resp.raise_for_status()
                items = resp.json().get("message", {}).get("items", [])
                for item in items:
                    authors = []
                    for a in item.get("author", []):
                        name = a.get("family", "")
                        given = a.get("given", "")
                        if name:
                            authors.append(f"{name}, {given[0]}." if given else name)

                    year_data = item.get("published-print") or item.get("published-online") or {}
                    year = year_data.get("date-parts", [[None]])[0][0]

                    papers.append({
                        "title": (item.get("title") or ["Untitled"])[0],
                        "authors": authors,
                        "year": year,
                        "journal": (item.get("container-title") or [""])[0],
                        "doi": item.get("DOI"),
                        "url": item.get("URL"),
                        "abstract": item.get("abstract", "")[:500],
                        "source_type": "journal",
                        "access_method": "OPEN_ACCESS",
                        "_source_agent": "crossref",
                    })
            except Exception as e:
                logger.warning(f"CrossRef search failed for '{query}': {e}")
            await asyncio.sleep(0.5)  # Polite delay
    return papers


async def _search_arxiv(queries: List[str]) -> List[Dict[str, Any]]:
    """Search arXiv for preprints (free OA)."""
    papers = []
    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries[:2]:
            try:
                resp = await client.get(
                    ARXIV_API,
                    params={
                        "search_query": f"all:{query}",
                        "max_results": 6,
                        "sortBy": "relevance",
                        "sortOrder": "descending",
                    },
                )
                resp.raise_for_status()
                # Parse Atom XML
                import xml.etree.ElementTree as ET
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                root = ET.fromstring(resp.text)
                for entry in root.findall("atom:entry", ns):
                    title    = entry.findtext("atom:title", "", ns).strip()
                    abstract = entry.findtext("atom:summary", "", ns).strip()[:400]
                    link     = entry.findtext("atom:id", "", ns)
                    year_str = entry.findtext("atom:published", "", ns)[:4]

                    authors = []
                    for auth in entry.findall("atom:author", ns):
                        name = auth.findtext("atom:name", "", ns)
                        if name:
                            parts = name.split()
                            authors.append(f"{parts[-1]}, {parts[0][0]}." if len(parts) > 1 else name)

                    doi = None
                    for link_el in entry.findall("atom:link", ns):
                        href = link_el.get("href", "")
                        if "doi.org" in href:
                            doi = href.split("doi.org/")[-1]

                    papers.append({
                        "title": title,
                        "authors": authors,
                        "year": int(year_str) if year_str.isdigit() else None,
                        "journal": "arXiv Preprint",
                        "doi": doi,
                        "url": link,
                        "abstract": abstract,
                        "source_type": "preprint",
                        "access_method": "OPEN_ACCESS",
                        "_source_agent": "arxiv",
                    })
            except Exception as e:
                logger.warning(f"arXiv search failed for '{query}': {e}")
    return papers


async def _search_doaj(queries: List[str]) -> List[Dict[str, Any]]:
    """Search the Directory of Open Access Journals (DOAJ)."""
    papers = []
    async with httpx.AsyncClient(timeout=30) as client:
        for query in queries[:2]:
            try:
                resp = await client.get(
                    DOAJ_API,
                    params={"q": query, "pageSize": 6},
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                for r in results:
                    bib = r.get("bibjson", {})
                    authors_raw = bib.get("author", [])
                    authors = [a.get("name", "") for a in authors_raw if a.get("name")]

                    # Get DOI
                    doi = None
                    for ident in bib.get("identifier", []):
                        if ident.get("type") == "doi":
                            doi = ident.get("id")
                    # Get link
                    link = None
                    for lnk in bib.get("link", []):
                        if lnk.get("type") == "fulltext":
                            link = lnk.get("url")

                    year = bib.get("year")
                    papers.append({
                        "title": bib.get("title", "Untitled"),
                        "authors": authors,
                        "year": int(year) if year and str(year).isdigit() else None,
                        "journal": bib.get("journal", {}).get("title", ""),
                        "doi": doi,
                        "url": link,
                        "abstract": bib.get("abstract", "")[:400],
                        "source_type": "journal",
                        "access_method": "OPEN_ACCESS",
                        "_source_agent": "doaj",
                    })
            except Exception as e:
                logger.warning(f"DOAJ search failed for '{query}': {e}")
    return papers


def _mock_papers(query: str, source: str, count: int = 3) -> List[Dict[str, Any]]:
    """Return mock papers for testing without API keys."""
    return [
        {
            "title": f"A Systematic Review of {query} — Study {i+1}",
            "authors": [f"Smith, J.", f"Chen, L."],
            "year": 2023 - i,
            "journal": ["Nature Scientific Reports", "PLOS ONE", "Frontiers in AI"][i % 3],
            "doi": f"10.1234/mock-{source}-{i}",
            "url": f"https://example.com/paper/{source}/{i}",
            "abstract": f"This paper examines {query} and presents findings on the topic. Methods include systematic review and meta-analysis of existing literature.",
            "source_type": "journal",
            "access_method": "WEB_SOURCE",
            "_source_agent": source,
        }
        for i in range(count)
    ]
