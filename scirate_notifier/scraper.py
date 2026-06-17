"""SciRate HTML scraper for top arXiv papers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from scirate_notifier.http_client import fetch_html

logger = logging.getLogger(__name__)

SCIRATE_BASE = "https://scirate.com"
REQUEST_TIMEOUT = 20

# Paper container selectors (tried in order; SciRate markup may vary):
#   ul.papers .row  — current layout on scirate.com/arxiv/* (2024+)
#   li.paper        — same rows as list items
#   div.paper       — legacy layout
PAPER_CONTAINER_SELECTORS = ("ul.papers .row", "li.paper", "div.paper")

# Title link: .title a — href contains /arxiv/{id}
TITLE_LINK_SELECTOR = ".title a"

# Scite count: button.count inside .scites-count (current layout)
SCITE_SELECTORS = (
    ".scites-count button.count",
    "button.btn-default.count",
    ".scites_count",
    ".num-scites",
    "a.scite-button",
    "[class*='scite']",
)

# Authors: .authors a — one link per author
AUTHORS_SELECTOR = ".authors a"

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    scites: int
    url: str
    abstract_url: str
    category: str


def fetch_top_papers(
    category: str,
    range_days: int,
    session: requests.Session | None = None,
) -> list[Paper]:
    """Fetch top papers for a SciRate arXiv category over the given day range."""
    url = f"{SCIRATE_BASE}/arxiv/{category}?range={range_days}"
    html = fetch_html(url, session=session)

    soup = BeautifulSoup(html, "lxml")
    containers = _find_paper_containers(soup)

    papers: list[Paper] = []
    for container in containers:
        try:
            paper = _parse_paper(container, category)
            if paper is not None:
                papers.append(paper)
        except Exception as exc:
            logger.warning("Skipping malformed paper entry: %s", exc)

    papers.sort(key=lambda p: p.scites, reverse=True)
    return papers


def fetch_all(
    categories: list[str],
    range_days: int,
    session: requests.Session | None = None,
) -> list[Paper]:
    """Fetch papers across categories, de-duplicating by arxiv_id (max scites wins)."""
    by_id: dict[str, Paper] = {}
    http = session or requests.Session()

    for category in categories:
        for paper in fetch_top_papers(category, range_days, session=http):
            existing = by_id.get(paper.arxiv_id)
            if existing is None or paper.scites > existing.scites:
                by_id[paper.arxiv_id] = paper

    return sorted(by_id.values(), key=lambda p: p.scites, reverse=True)


def _find_paper_containers(soup: BeautifulSoup) -> list[Tag]:
    for selector in PAPER_CONTAINER_SELECTORS:
        containers = soup.select(selector)
        if containers:
            return containers
    return []


def _parse_paper(container: Tag, category: str) -> Paper | None:
    title_link = container.select_one(TITLE_LINK_SELECTOR)
    if title_link is None:
        return None

    href = title_link.get("href", "")
    arxiv_id = _extract_arxiv_id(href)
    if not arxiv_id:
        return None

    title = title_link.get_text(strip=True)
    if not title:
        return None

    scites = _extract_scites(container)
    authors = _extract_authors(container)
    paper_url = urljoin(SCIRATE_BASE, href)
    abstract_url = f"https://arxiv.org/abs/{arxiv_id}"

    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        scites=scites,
        url=paper_url,
        abstract_url=abstract_url,
        category=category,
    )


def _extract_arxiv_id(href: str) -> str | None:
    segment = href.rstrip("/").split("/")[-1]
    match = _ARXIV_ID_RE.search(segment)
    if match:
        return match.group(1)
    match = _ARXIV_ID_RE.search(href)
    return match.group(1) if match else None


def _extract_scites(container: Tag) -> int:
    for selector in SCITE_SELECTORS:
        element = container.select_one(selector)
        if element is not None:
            count = _first_integer(element.get_text())
            if count is not None:
                return count
    return 0


def _extract_authors(container: Tag) -> list[str]:
    author_links = container.select(AUTHORS_SELECTOR)
    if author_links:
        return [_clean_author_name(link.get_text(strip=True)) for link in author_links]
    authors_el = container.select_one(".authors")
    if authors_el is None:
        return []
    text = authors_el.get_text(strip=True)
    if not text:
        return []
    return [_clean_author_name(name) for name in text.split(",") if name.strip()]


def _clean_author_name(name: str) -> str:
    return name.strip().rstrip(",")


def _first_integer(text: str) -> int | None:
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None
