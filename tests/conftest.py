"""
Shared fixtures for the offline test suite: a synthetic option chain (shaped
exactly like market.get_option_chain returns one, with no Greeks/IV so
select.py falls back to local Black-Scholes) and a stub of every market/
fundamentals call the selection and report pipelines make, so no test ever
touches the network.
"""
from __future__ import annotations

import copy
from datetime import date, timedelta

import pytest

from optionslab import fundamentals, market, select
from optionslab.bs import bs_price
from optionslab.config import load_config

SPOT = 100.0
SIGMA = 0.30
RATE = 0.043


def _contract(strike: float, option_type: str, expiration: str, *, quoted: bool = True) -> dict:
    """A chain entry shaped exactly like market.get_option_chain returns one:
    no Greeks and no IV, which is the common case that forces select.py to fall
    back to local Black-Scholes."""
    T = (date.fromisoformat(expiration) - date.today()).days / 365.0
    # float() throughout: Alpaca hands back plain JSON numbers, and letting
    # numpy scalars leak in from bs_price would make this fixture unrealistic.
    fair = float(bs_price(SPOT, strike, T, RATE, SIGMA, option_type))
    return {
        "symbol": f"TST{expiration.replace('-', '')}{option_type[0].upper()}{int(strike * 1000):08d}",
        "underlying": "TST",
        "expiration": expiration,
        "type": option_type,
        "strike": strike,
        "bid": round(fair * 0.99, 2) if quoted else None,
        "ask": round(fair * 1.01, 2) if quoted else None,
        "bid_size": 10 if quoted else 0,
        "ask_size": 10 if quoted else 0,
        "last_price": round(fair, 2),
        "implied_volatility": None,
        "delta": None,
        "gamma": None,
        "theta": None,
        "vega": None,
        "rho": None,
    }


@pytest.fixture
def leaps_expiration() -> str:
    """Inside the long_call window (180-730 DTE) from config.toml."""
    return (date.today() + timedelta(days=365)).isoformat()


@pytest.fixture
def call_chain(leaps_expiration: str) -> list[dict]:
    return [_contract(k, "call", leaps_expiration) for k in range(60, 141, 5)]


@pytest.fixture
def patched_config(monkeypatch: pytest.MonkeyPatch) -> dict:
    cfg = copy.deepcopy(load_config())
    cfg["math"]["monte_carlo_paths"] = 2_000
    monkeypatch.setattr(select, "load_config", lambda: cfg)
    return cfg


@pytest.fixture
def stub_market(monkeypatch: pytest.MonkeyPatch, call_chain: list[dict]) -> None:
    monkeypatch.setattr(market, "get_latest_price", lambda ticker: SPOT)
    monkeypatch.setattr(
        market,
        "get_option_chain",
        lambda ticker, **kwargs: call_chain,
    )
    monkeypatch.setattr(
        market,
        "get_account",
        lambda: {
            "status": "ACTIVE",
            "cash": 50_000.0,
            "buying_power": 50_000.0,
            "portfolio_value": 50_000.0,
        },
    )


@pytest.fixture
def daily_bars() -> list[dict]:
    """~450 daily closes on a steady uptrend, so SMA20 > SMA50 > SMA200 and
    price > SMA20 hold at the end — enough history for every indicator
    (SMA200, HV90 + its 1-year percentile) to resolve to a real number rather
    than NaN."""
    start = date.today() - timedelta(days=450)
    bars = []
    price = 70.0
    for i in range(450):
        price *= 1.0006  # gentle steady drift upward
        d = start + timedelta(days=i)
        bars.append(
            {
                "date": d.isoformat(),
                "open": price * 0.995,
                "high": price * 1.01,
                "low": price * 0.99,
                "close": price,
                "volume": 1_000_000,
            }
        )
    return bars


@pytest.fixture
def stub_report_data(monkeypatch: pytest.MonkeyPatch, daily_bars: list[dict]) -> None:
    """Stubs the two extra seams build_report_context hits beyond select.py:
    daily bars (for indicators.compute_all) and fundamentals (yfinance)."""
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": f"{symbol} Inc.",
            "market_cap": 2_500_000_000_000.0,
            "sector": "Technology",
            "next_earnings_date": None,
        },
    )
