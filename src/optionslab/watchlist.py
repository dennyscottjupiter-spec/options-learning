"""
Persistent watchlist for the dashboard. Plain JSON file (gitignored, since it's
per-machine state, not project config) seeded from config.toml's [watchlist]
section the first time it's read.
"""
from __future__ import annotations

import json
from pathlib import Path

from optionslab.config import load_config

WATCHLIST_PATH = Path(__file__).resolve().parents[2] / "watchlist.json"


def get_watchlist() -> list[str]:
    if not WATCHLIST_PATH.exists():
        seed = list(load_config()["watchlist"]["tickers"])
        _save(seed)
        return seed
    return json.loads(WATCHLIST_PATH.read_text())


def add_ticker(ticker: str) -> list[str]:
    ticker = ticker.strip().upper()
    tickers = get_watchlist()
    if ticker and ticker not in tickers:
        tickers.append(ticker)
        _save(tickers)
    return tickers


def remove_ticker(ticker: str) -> list[str]:
    ticker = ticker.strip().upper()
    tickers = [t for t in get_watchlist() if t != ticker]
    _save(tickers)
    return tickers


def _save(tickers: list[str]) -> None:
    WATCHLIST_PATH.write_text(json.dumps(tickers, indent=2))
