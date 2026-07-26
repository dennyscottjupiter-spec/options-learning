"""
Fundamentals Alpaca doesn't provide: market cap, sector, next earnings date.

Uses `yfinance` (community package, ~18k GitHub stars, the de-facto standard for
this data — there is no free official alternative; Alpaca's own API has none of
these fields). Cached to disk for a day since these change slowly.
"""
from __future__ import annotations

from datetime import date

import yfinance as yf

from optionslab.cache import cache_get, cache_set

FUNDAMENTALS_CACHE_TTL_SECONDS = 24 * 60 * 60


def get_fundamentals(symbol: str) -> dict:
    """Returns {market_cap, sector, next_earnings_date} for `symbol`.
    next_earnings_date is None if yfinance has no upcoming date on file."""
    cache_key = f"fundamentals:{symbol}:{date.today().isoformat()}"
    cached = cache_get(cache_key, FUNDAMENTALS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    info = ticker.info
    calendar = ticker.calendar or {}
    earnings_dates = calendar.get("Earnings Date") or []
    next_earnings = earnings_dates[0].isoformat() if earnings_dates else None

    result = {
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
        "next_earnings_date": next_earnings,
    }
    cache_set(cache_key, result)
    return result
