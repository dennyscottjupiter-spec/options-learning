"""
Technical indicators computed from daily closes: SMA 20/50/200, RSI(14),
historical volatility (30d/90d, with a 1-year percentile so "30% HV" has
context), 52-week range, and a plain-English directional bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def sma(closes: pd.Series, window: int) -> pd.Series:
    return closes.rolling(window).mean()


def rsi(closes: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's RSI: smoothed average gain / average loss over `window` periods."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    return result.where(avg_loss != 0, 100.0)


def historical_volatility(closes: pd.Series, window: int) -> pd.Series:
    """Annualized stdev of log returns over a trailing `window`-day period."""
    log_returns = np.log(closes / closes.shift(1))
    return log_returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def hv_percentile(hv_series: pd.Series, lookback: int = TRADING_DAYS_PER_YEAR) -> float:
    """Where the most recent HV value ranks within its trailing `lookback`-day
    history, as a 0-100 percentile. Answers 'is today's vol high or low for
    this stock', not just 'what is it'."""
    recent = hv_series.dropna().tail(lookback)
    if len(recent) < 2:
        return float("nan")
    current = recent.iloc[-1]
    return float((recent < current).mean() * 100)


def fifty_two_week_range(bars: list[dict]) -> dict:
    closes = [b["close"] for b in bars[-TRADING_DAYS_PER_YEAR:]]
    return {"low_52w": min(closes), "high_52w": max(closes)}


def directional_bias(closes: pd.Series) -> str:
    """A plain-English read on trend from SMA stacking. Not a signal to trade
    on by itself — the report explains that explicitly."""
    price = closes.iloc[-1]
    sma20 = sma(closes, 20).iloc[-1]
    sma50 = sma(closes, 50).iloc[-1]
    sma200 = sma(closes, 200).iloc[-1]

    if any(pd.isna(v) for v in (sma20, sma50, sma200)):
        return "insufficient history"

    if price > sma20 > sma50 > sma200:
        return "bullish"
    if price < sma20 < sma50 < sma200:
        return "bearish"
    return "mixed"


def compute_all(bars: list[dict]) -> dict:
    """Convenience wrapper: runs every indicator against a bars list (as
    returned by market.get_daily_bars) and returns the latest values."""
    df = pd.DataFrame(bars)
    closes = df["close"]

    hv30 = historical_volatility(closes, 30)
    hv90 = historical_volatility(closes, 90)

    return {
        "sma20": sma(closes, 20).iloc[-1],
        "sma50": sma(closes, 50).iloc[-1],
        "sma200": sma(closes, 200).iloc[-1],
        "rsi14": rsi(closes, 14).iloc[-1],
        "hv30": hv30.iloc[-1],
        "hv30_percentile": hv_percentile(hv30),
        "hv90": hv90.iloc[-1],
        "hv90_percentile": hv_percentile(hv90),
        "directional_bias": directional_bias(closes),
        **fifty_two_week_range(bars),
    }
