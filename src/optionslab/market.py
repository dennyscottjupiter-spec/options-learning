"""
Alpaca REST access: stock bars, option chain snapshots, paper account, positions.

Every read goes through a small disk cache (cache/) keyed by request signature,
so repeated lookups for the same ticker/expiry within the cache window cost zero
extra API calls — important on the free feed's 200 req/min limit, and an option
chain snapshot alone can be dozens of contracts in one call.
"""
from __future__ import annotations

import time
from datetime import date, datetime
from functools import lru_cache

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import OptionChainRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

from optionslab.cache import cache_get, cache_set
from optionslab.config import load_config
from optionslab.creds import get_alpaca_credentials

BARS_CACHE_TTL_SECONDS = 15 * 60
CHAIN_CACHE_TTL_SECONDS = 2 * 60


class RateLimitTracker:
    """Counts Alpaca data-API calls in the trailing 60s window and warns before
    the free plan's 200 req/min cap would be hit."""

    def __init__(self, limit_per_min: int) -> None:
        self.limit_per_min = limit_per_min
        self._call_times: list[float] = []

    def record(self) -> None:
        now = time.monotonic()
        self._call_times = [t for t in self._call_times if now - t < 60]
        self._call_times.append(now)
        if len(self._call_times) > self.limit_per_min:
            raise RuntimeError(
                f"Alpaca rate limit exceeded: {len(self._call_times)} calls in the "
                f"last 60s (limit {self.limit_per_min}/min). Slow down or cache more."
            )


@lru_cache(maxsize=1)
def _rate_limiter() -> RateLimitTracker:
    cfg = load_config()
    return RateLimitTracker(cfg["alpaca"]["rate_limit_per_min"])


@lru_cache(maxsize=1)
def _trading_client() -> TradingClient:
    api_key, api_secret = get_alpaca_credentials()
    return TradingClient(api_key, api_secret, paper=True)


@lru_cache(maxsize=1)
def _stock_client() -> StockHistoricalDataClient:
    api_key, api_secret = get_alpaca_credentials()
    return StockHistoricalDataClient(api_key, api_secret)


@lru_cache(maxsize=1)
def _option_client() -> OptionHistoricalDataClient:
    api_key, api_secret = get_alpaca_credentials()
    return OptionHistoricalDataClient(api_key, api_secret)


def get_account() -> dict:
    """Read-only paper account snapshot: cash, buying power, portfolio value."""
    _rate_limiter().record()
    account = _trading_client().get_account()
    return {
        "status": str(account.status),
        "cash": float(account.cash),
        "buying_power": float(account.buying_power),
        "portfolio_value": float(account.portfolio_value),
    }


def get_positions() -> list[dict]:
    """Read-only paper positions: symbol, quantity, cost basis, market value, P/L."""
    _rate_limiter().record()
    positions = _trading_client().get_all_positions()
    return [
        {
            "symbol": p.symbol,
            "qty": float(p.qty),
            "avg_entry_price": float(p.avg_entry_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "current_price": float(p.current_price),
        }
        for p in positions
    ]


def get_daily_bars(symbol: str, lookback_days: int = 400) -> list[dict]:
    """Daily OHLCV bars for `symbol`, most recent `lookback_days` calendar days.
    Cached to disk for BARS_CACHE_TTL_SECONDS."""
    cache_key = f"bars:{symbol}:{lookback_days}:{date.today().isoformat()}"
    cached = cache_get(cache_key, BARS_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    _rate_limiter().record()
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        - _days_delta(lookback_days),
    )
    barset = _stock_client().get_stock_bars(request)
    bars = [
        {
            "date": bar.timestamp.date().isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in barset[symbol]
    ]
    cache_set(cache_key, bars)
    return bars


def _days_delta(days: int):
    from datetime import timedelta

    return timedelta(days=days)


def get_latest_price(symbol: str) -> float:
    """Most recent daily close for `symbol` — used as the underlying spot price."""
    bars = get_daily_bars(symbol, lookback_days=10)
    if not bars:
        raise ValueError(f"No recent bars for {symbol}; is the market ever open for it?")
    return bars[-1]["close"]


def get_option_chain(
    underlying_symbol: str,
    expiration_date: str | None = None,
    expiration_date_gte: str | None = None,
    expiration_date_lte: str | None = None,
) -> list[dict]:
    """Option chain snapshot: bid/ask, last trade, implied volatility, and Greeks
    per contract. Cached to disk for CHAIN_CACHE_TTL_SECONDS.

    Note: Alpaca's snapshot has no open-interest field — liquidity is judged by
    quoted bid/ask size and spread instead (see config.toml [liquidity]).
    """
    cfg = load_config()
    cache_key = (
        f"chain:{underlying_symbol}:{expiration_date}:"
        f"{expiration_date_gte}:{expiration_date_lte}"
    )
    cached = cache_get(cache_key, CHAIN_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    _rate_limiter().record()
    request = OptionChainRequest(
        underlying_symbol=underlying_symbol,
        feed=cfg["alpaca"]["data_feed"],
        expiration_date=expiration_date,
        expiration_date_gte=expiration_date_gte,
        expiration_date_lte=expiration_date_lte,
    )
    snapshots = _option_client().get_option_chain(request)

    contracts = []
    for occ_symbol, snap in snapshots.items():
        parsed = _parse_occ_symbol(occ_symbol)
        quote = snap.latest_quote
        trade = snap.latest_trade
        greeks = snap.greeks
        contracts.append(
            {
                "symbol": occ_symbol,
                "underlying": parsed["underlying"],
                "expiration": parsed["expiration"],
                "type": parsed["type"],
                "strike": parsed["strike"],
                "bid": quote.bid_price if quote else None,
                "ask": quote.ask_price if quote else None,
                "bid_size": quote.bid_size if quote else None,
                "ask_size": quote.ask_size if quote else None,
                "last_price": trade.price if trade else None,
                "implied_volatility": snap.implied_volatility,
                "delta": greeks.delta if greeks else None,
                "gamma": greeks.gamma if greeks else None,
                "theta": greeks.theta if greeks else None,
                "vega": greeks.vega if greeks else None,
                "rho": greeks.rho if greeks else None,
            }
        )
    cache_set(cache_key, contracts)
    return contracts


def _parse_occ_symbol(occ_symbol: str) -> dict:
    """Parses an OCC option symbol, e.g. 'AAPL240119C00150000' ->
    underlying=AAPL, expiration=2024-01-19, type=call, strike=150.0."""
    i = 0
    while i < len(occ_symbol) and not occ_symbol[i].isdigit():
        i += 1
    underlying = occ_symbol[:i]
    rest = occ_symbol[i:]
    yy, mm, dd = rest[0:2], rest[2:4], rest[4:6]
    cp = rest[6]
    strike_raw = rest[7:]
    return {
        "underlying": underlying,
        "expiration": f"20{yy}-{mm}-{dd}",
        "type": "call" if cp == "C" else "put",
        "strike": int(strike_raw) / 1000.0,
    }
