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
    """Returns {market_cap, sector, next_earnings_date, next_ex_dividend_date}
    for `symbol`. Both date fields are None if yfinance has no upcoming date
    on file."""
    cache_key = f"fundamentals:{symbol}:{date.today().isoformat()}"
    cached = cache_get(cache_key, FUNDAMENTALS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    info = ticker.info
    calendar = ticker.calendar or {}
    earnings_dates = calendar.get("Earnings Date") or []
    next_earnings = earnings_dates[0].isoformat() if earnings_dates else None

    ex_dividend = calendar.get("Ex-Dividend Date")
    if isinstance(ex_dividend, list):
        ex_dividend = ex_dividend[0] if ex_dividend else None
    next_ex_dividend = ex_dividend.isoformat() if ex_dividend else None

    result = {
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "market_cap": info.get("marketCap"),
        "sector": info.get("sector"),
        "next_earnings_date": next_earnings,
        "next_ex_dividend_date": next_ex_dividend,
    }
    cache_set(cache_key, result)
    return result
