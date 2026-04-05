from __future__ import annotations

from pathlib import Path

from app.config.settings import WATCHLIST_PATH, load_watchlist
from app.schemas import WatchlistCompany


def load_company_registry(path: Path | None = None) -> list[WatchlistCompany]:
    """Read the configured watchlist and return company objects."""
    return load_watchlist(path or WATCHLIST_PATH)


def get_watchlist_companies() -> list[WatchlistCompany]:
    """Return companies from the ingestion registry."""
    return load_company_registry()
