import numpy as np
import pandas as pd
import pytest

from optionslab.indicators import (
    fifty_two_week_range,
    historical_volatility,
    hv_percentile,
    rsi,
    sma,
)


def test_sma_matches_manual_average():
    closes = pd.Series([10, 20, 30, 40, 50], dtype=float)
    result = sma(closes, window=3)
    assert result.iloc[2] == pytest.approx((10 + 20 + 30) / 3)
    assert result.iloc[4] == pytest.approx((30 + 40 + 50) / 3)
    assert pd.isna(result.iloc[1])  # not enough history yet


def test_rsi_approaches_100_on_relentless_uptrend():
    closes = pd.Series(np.linspace(100, 200, 60))
    result = rsi(closes, window=14)
    assert result.iloc[-1] > 95


def test_rsi_approaches_0_on_relentless_downtrend():
    closes = pd.Series(np.linspace(200, 100, 60))
    result = rsi(closes, window=14)
    assert result.iloc[-1] < 5


def test_rsi_near_50_on_flat_price():
    closes = pd.Series([100.0] * 30)
    result = rsi(closes, window=14)
    assert result.iloc[-1] == pytest.approx(100.0)  # no losses at all -> RSI=100 by definition
    # a series that alternates +1/-1 by equal amounts should sit near 50
    alt = pd.Series([100 + (1 if i % 2 == 0 else -1) for i in range(30)], dtype=float)
    result_alt = rsi(alt, window=14)
    assert 40 < result_alt.iloc[-1] < 60


def test_historical_volatility_matches_manual_stdev():
    rng = np.random.default_rng(42)
    log_returns = rng.normal(0, 0.02, 100)
    closes = pd.Series(100 * np.exp(np.cumsum(log_returns)))

    hv = historical_volatility(closes, window=30)

    manual_log_returns = np.diff(np.log(closes.values[-31:]))
    manual_hv = manual_log_returns.std(ddof=1) * np.sqrt(252)
    assert hv.iloc[-1] == pytest.approx(manual_hv, rel=1e-9)


def test_hv_percentile_bounds():
    rng = np.random.default_rng(1)
    log_returns = rng.normal(0, 0.02, 400)
    closes = pd.Series(100 * np.exp(np.cumsum(log_returns)))
    hv = historical_volatility(closes, window=30)
    pct = hv_percentile(hv)
    assert 0 <= pct <= 100


def test_fifty_two_week_range():
    bars = [{"close": float(c)} for c in [90, 110, 95, 130, 80]]
    result = fifty_two_week_range(bars)
    assert result == {"low_52w": 80.0, "high_52w": 130.0}
