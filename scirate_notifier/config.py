"""Configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    ntfy_topic: str
    ntfy_server: str = "https://ntfy.sh"
    scirate_categories: list[str] | None = None
    scirate_range_days: int = 1
    top_n: int = 5
    min_scites: int = 1
    ntfy_priority: str = "default"

    def __post_init__(self) -> None:
        if self.scirate_categories is None:
            object.__setattr__(self, "scirate_categories", ["quant-ph"])

    @classmethod
    def from_env(cls) -> Config:
        topic = os.environ.get("NTFY_TOPIC", "").strip()
        if not topic:
            raise ConfigError(
                "NTFY_TOPIC is required. Set it to your private ntfy topic name."
            )

        categories_raw = os.environ.get("SCIRATE_CATEGORIES", "quant-ph").strip()
        categories = [c.strip() for c in categories_raw.split(",") if c.strip()]
        if not categories:
            raise ConfigError("SCIRATE_CATEGORIES must contain at least one category.")

        return cls(
            ntfy_topic=topic,
            ntfy_server=os.environ.get("NTFY_SERVER", "https://ntfy.sh").strip(),
            scirate_categories=categories,
            scirate_range_days=_parse_int("SCIRATE_RANGE_DAYS", default=1),
            top_n=_parse_int("TOP_N", default=5),
            min_scites=_parse_int("MIN_SCITES", default=1),
            ntfy_priority=os.environ.get("NTFY_PRIORITY", "default").strip(),
        )


def _parse_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
