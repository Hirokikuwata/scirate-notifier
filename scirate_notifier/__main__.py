"""CLI entrypoint: python -m scirate_notifier"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace

import requests

from scirate_notifier.arxiv_client import fetch_recent_all
from scirate_notifier.config import Config, ConfigError
from scirate_notifier.notifier import send_notification
from scirate_notifier.scraper import Paper, fetch_all

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        config = Config.from_env()
    except ConfigError as exc:
        logger.error("%s", exc)
        return 1

    if args.category:
        config = replace(config, scirate_categories=args.category)
    if args.top_n is not None:
        config = replace(config, top_n=args.top_n)

    papers, using_fallback = _fetch_papers(config)
    if papers is None:
        return 1

    if using_fallback:
        # arXiv fallback papers all have scites=0; skip the scites filter.
        top_papers = papers[: config.top_n]
    else:
        filtered = [p for p in papers if p.scites >= config.min_scites]
        top_papers = filtered[: config.top_n]

    logger.info(
        "Fetched %d paper(s), showing top %d (source=%s)",
        len(papers),
        len(top_papers),
        "arxiv-fallback" if using_fallback else "scirate",
    )

    if args.dry_run:
        _print_dry_run(top_papers, config, using_fallback)
        return 0

    try:
        send_notification(config, top_papers, using_fallback=using_fallback)
    except Exception as exc:
        logger.error("Failed to send notification: %s", exc)
        return 1

    return 0


def _fetch_papers(config: Config) -> tuple[list[Paper] | None, bool]:
    """Return (papers, using_fallback). papers=None signals a fatal error."""
    try:
        papers = fetch_all(config.scirate_categories, config.scirate_range_days)
        return papers, False
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 403:
            logger.warning(
                "SciRate returned 403 (IP blocked). Falling back to arXiv API "
                "(recent papers, no scite counts)."
            )
        else:
            logger.warning("SciRate fetch failed (%s). Falling back to arXiv API.", exc)
    except Exception as exc:
        logger.warning("SciRate fetch failed: %s. Falling back to arXiv API.", exc)

    try:
        papers = fetch_recent_all(config.scirate_categories, max_results=config.top_n * 2)
        return papers, True
    except Exception as exc:
        logger.error("arXiv fallback also failed: %s", exc)
        return None, False


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch top SciRate papers and notify via ntfy.sh",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results to stdout instead of sending a notification",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Override TOP_N: max papers to include",
    )
    parser.add_argument(
        "--category",
        action="append",
        dest="category",
        metavar="CAT",
        help="Override SCIRATE_CATEGORIES (repeatable, e.g. quant-ph)",
    )
    return parser.parse_args(argv)


def _print_dry_run(papers: list[Paper], config: Config, using_fallback: bool = False) -> None:
    source = "arXiv (fallback)" if using_fallback else "SciRate"
    print(f"[dry-run] source={source} categories={config.scirate_categories} top_n={config.top_n}")
    if not papers:
        print("No papers above threshold.")
        return
    for paper in papers:
        label = "recent" if using_fallback else f"{paper.scites} scites"
        print(f"• {label} — {paper.title}")
        print(f"  {paper.abstract_url}")


if __name__ == "__main__":
    sys.exit(main())
