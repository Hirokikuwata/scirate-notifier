"""Send paper digests via ntfy.sh."""

from __future__ import annotations

import logging
from textwrap import shorten

import requests

from scirate_notifier.config import Config
from scirate_notifier.scraper import Paper

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
TITLE_MAX_LEN = 120

_TITLES = {
    "scirate": "SciRate {categories} top papers",
    "arxiv": "arXiv {categories} recent papers",
    "arxiv-fallback": "arXiv {categories} recent papers (SciRate unavailable)",
}
_NO_PAPERS_TITLES = {
    "scirate": "SciRate {categories}: no top papers today",
    "arxiv": "arXiv {categories}: no recent papers found",
    "arxiv-fallback": "arXiv {categories}: no papers found (SciRate unavailable)",
}


def send_notification(
    config: Config,
    papers: list[Paper],
    *,
    source: str = "scirate",
) -> None:
    """POST a digest to the configured ntfy topic."""
    categories = sorted({p.category for p in papers}) if papers else config.scirate_categories
    category_label = ", ".join(categories)

    title_tmpl = (_NO_PAPERS_TITLES if not papers else _TITLES).get(
        source, _TITLES["scirate"]
    )
    title = title_tmpl.format(categories=category_label)

    if not papers:
        _post(
            config,
            title=title,
            body="No papers above threshold today.",
            click_url=f"{config.ntfy_server}/{config.ntfy_topic}",
            priority="low",
        )
        return

    lines: list[str] = []
    for paper in papers:
        short_title = shorten(paper.title, width=TITLE_MAX_LEN, placeholder="...")
        if source == "scirate":
            lines.append(f"• {paper.scites}⭐ {short_title}")
        else:
            lines.append(f"• {short_title}")
        if paper.authors:
            lines.append(f"  {_format_authors(paper.authors)}")
        lines.append(f"  {paper.abstract_url}")

    body = "\n".join(lines)
    click_url = papers[0].abstract_url

    _post(
        config,
        title=title,
        body=body,
        click_url=click_url,
        priority=config.ntfy_priority,
    )
    logger.info("Sent notification: source=%s papers=%d", source, len(papers))


def _post(
    config: Config,
    title: str,
    body: str,
    click_url: str,
    priority: str,
) -> None:
    url = f"{config.ntfy_server.rstrip('/')}/{config.ntfy_topic}"
    headers = {
        "Title": _ascii_safe(title),
        "Priority": _ascii_safe(priority),
        "Tags": "microscope",
        "Click": _ascii_safe(click_url),
        "Markdown": "yes",
    }

    response = requests.post(
        url,
        data=body.encode("utf-8"),
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()


def _format_authors(authors: list[str], max_shown: int = 3) -> str:
    shown = authors[:max_shown]
    rest = len(authors) - len(shown)
    label = ", ".join(shown)
    return f"{label} +{rest} more" if rest > 0 else label


def _ascii_safe(value: str) -> str:
    return value.encode("ascii", errors="replace").decode("ascii")
