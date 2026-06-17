"""CLI entrypoint: python -m scirate_notifier"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace

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

    try:
        papers = fetch_all(config.scirate_categories, config.scirate_range_days)
    except Exception as exc:
        logger.error("Failed to fetch papers: %s", exc)
        return 1

    filtered = [p for p in papers if p.scites >= config.min_scites]
    top_papers = filtered[: config.top_n]

    logger.info(
        "Fetched %d paper(s), %d above min scites (%d), showing top %d",
        len(papers),
        len(filtered),
        config.min_scites,
        len(top_papers),
    )

    if args.dry_run:
        _print_dry_run(top_papers, config)
        return 0

    try:
        send_notification(config, top_papers)
    except Exception as exc:
        logger.error("Failed to send notification: %s", exc)
        return 1

    return 0


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


def _print_dry_run(papers: list[Paper], config: Config) -> None:
    print(f"[dry-run] categories={config.scirate_categories} top_n={config.top_n}")
    if not papers:
        print("No papers above threshold.")
        return
    for paper in papers:
        print(f"• {paper.scites} scites — {paper.title}")
        print(f"  {paper.abstract_url}")


if __name__ == "__main__":
    sys.exit(main())
