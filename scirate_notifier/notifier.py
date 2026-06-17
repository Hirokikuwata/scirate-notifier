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


def send_notification(config: Config, papers: list[Paper]) -> None:
    """POST a digest to the configured ntfy topic."""
    if not papers:
        _post(
            config,
            title="SciRate: no top papers today",
            body="No papers above threshold today.",
            click_url=f"{config.ntfy_server}/{config.ntfy_topic}",
            priority="low",
        )
        return

    categories = sorted({p.category for p in papers})
    category_label = ", ".join(categories)
    title = f"SciRate {category_label} top papers"

    lines: list[str] = []
    for paper in papers:
        short_title = shorten(paper.title, width=TITLE_MAX_LEN, placeholder="...")
        lines.append(f"• {paper.scites}⭐ {short_title}")
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
    logger.info("Sent notification with %d paper(s)", len(papers))


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


def _ascii_safe(value: str) -> str:
    return value.encode("ascii", errors="replace").decode("ascii")
