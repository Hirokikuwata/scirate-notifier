"""Fallback paper source using the arXiv public Atom API.

Used when SciRate is unavailable (e.g. IP-blocked on GitHub Actions).
Papers are sorted by submission date (newest first) instead of scite count.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import requests

from scirate_notifier.scraper import Paper

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "https://export.arxiv.org/api/query"
REQUEST_TIMEOUT = 30

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")


def fetch_recent_papers(category: str, max_results: int = 20) -> list[Paper]:
    """Return the most recently submitted arXiv papers in *category*.

    scites is always 0 because the arXiv API does not expose SciRate data.
    """
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
        "start": 0,
    }
    response = requests.get(ARXIV_API_BASE, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    papers: list[Paper] = []
    for entry in root.findall("atom:entry", _NS):
        try:
            paper = _parse_entry(entry, category)
            if paper is not None:
                papers.append(paper)
        except Exception as exc:
            logger.warning("Skipping arXiv entry: %s", exc)

    return papers


def fetch_recent_all(categories: list[str], max_results: int = 20) -> list[Paper]:
    """Fetch recent papers across categories, de-duplicating by arxiv_id."""
    by_id: dict[str, Paper] = {}
    for category in categories:
        for paper in fetch_recent_papers(category, max_results=max_results):
            if paper.arxiv_id not in by_id:
                by_id[paper.arxiv_id] = paper
    # Preserve submission-date order (API already returns newest first,
    # dict insertion order is stable in Python 3.7+).
    return list(by_id.values())


def _parse_entry(entry: ET.Element, category: str) -> Paper | None:
    id_el = entry.find("atom:id", _NS)
    if id_el is None or not id_el.text:
        return None

    match = _ARXIV_ID_RE.search(id_el.text)
    if not match:
        return None
    arxiv_id = match.group(1)

    title_el = entry.find("atom:title", _NS)
    title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""
    if not title:
        return None

    authors = [
        name.text.strip()
        for author in entry.findall("atom:author", _NS)
        for name in (author.find("atom:name", _NS),)
        if name is not None and name.text
    ]

    abstract_url = f"https://arxiv.org/abs/{arxiv_id}"
    scirate_url = f"https://scirate.com/arxiv/{arxiv_id}"

    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        scites=0,
        url=scirate_url,
        abstract_url=abstract_url,
        category=category,
    )
