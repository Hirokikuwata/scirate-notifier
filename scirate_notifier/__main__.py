"""CLI entrypoint: python -m scirate_notifier"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace

from scirate_notifier.arxiv_client import fetch_recent_all
from scirate_notifier.config import Config, ConfigError
from scirate_notifier.notifier import send_notification
from scirate_notifier.scraper import Paper, fetch_all

logger = logging.getLogger(__name__)

# Source labels returned by _fetch_papers:
#   "scirate"        – fetched from SciRate (has scite counts)
#   "arxiv"          – explicitly requested arXiv run
#   "arxiv-fallback" – SciRate failed, fell back to arXiv
SOURCE_SCIRATE = "scirate"
SOURCE_ARXIV = "arxiv"
SOURCE_ARXIV_FALLBACK = "arxiv-fallback"


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

    papers, source = _fetch_papers(config, args.source)
    if papers is None:
        return 1

    if source == SOURCE_SCIRATE:
        filtered = [p for p in papers if p.scites >= config.min_scites]
        top_papers = filtered[: config.top_n]
    else:
        # arXiv papers have scites=0; skip the scites filter.
        top_papers = papers[: config.top_n]

    logger.info(
        "Fetched %d paper(s), showing top %d (source=%s)",
        len(papers),
        len(top_papers),
        source,
    )

    if args.dry_run:
        _print_dry_run(top_papers, config, source)
        return 0

    try:
        send_notification(config, top_papers, source=source)
    except Exception as exc:
        logger.error("Failed to send notification: %s", exc)
        return 1

    return 0


def _fetch_papers(config: Config, source_arg: str) -> tuple[list[Paper] | None, str]:
    """Fetch papers from the requested source.

    Returns (papers, actual_source). papers=None signals a fatal error.
    """
    if source_arg == SOURCE_ARXIV:
        try:
            papers = fetch_recent_all(
                config.scirate_categories, max_results=config.top_n * 2
            )
            return papers, SOURCE_ARXIV
        except Exception as exc:
            logger.error("arXiv fetch failed: %s", exc)
            return None, SOURCE_ARXIV

    if source_arg == SOURCE_SCIRATE:
        try:
            papers = fetch_all(config.scirate_categories, config.scirate_range_days)
            return papers, SOURCE_SCIRATE
        except Exception as exc:
            logger.error("SciRate fetch failed: %s", exc)
            return None, SOURCE_SCIRATE

    # auto: try SciRate first, fall back to arXiv.
    try:
        papers = fetch_all(config.scirate_categories, config.scirate_range_days)
        return papers, SOURCE_SCIRATE
    except Exception as exc:
        logger.warning("SciRate fetch failed (%s). Falling back to arXiv API.", exc)

    try:
        papers = fetch_recent_all(
            config.scirate_categories, max_results=config.top_n * 2
        )
        return papers, SOURCE_ARXIV_FALLBACK
    except Exception as exc:
        logger.error("arXiv fallback also failed: %s", exc)
        return None, "auto"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch top SciRate/arXiv papers and notify via ntfy.sh",
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
        help="Override SCIRATE_CATEGORIES (repeatable, e.g. quant-ph hep-th)",
    )
    parser.add_argument(
        "--source",
        choices=["auto", SOURCE_SCIRATE, SOURCE_ARXIV],
        default="auto",
        help=(
            "Paper source: auto (try SciRate, fall back to arXiv), "
            "scirate (SciRate scite-sorted only), "
            "arxiv (arXiv recent submissions only)"
        ),
    )
    return parser.parse_args(argv)


def _print_dry_run(papers: list[Paper], config: Config, source: str) -> None:
    print(f"[dry-run] source={source} categories={config.scirate_categories} top_n={config.top_n}")
    if not papers:
        print("No papers above threshold.")
        return
    for paper in papers:
        if source == SOURCE_SCIRATE:
            label = f"{paper.scites} scites"
        else:
            label = "recent"
        print(f"• {label} — {paper.title}")
        if paper.authors:
            print(f"  {', '.join(paper.authors[:3])}")
        print(f"  {paper.abstract_url}")


if __name__ == "__main__":
    sys.exit(main())
