import math

import pytest

from optionslab.bs import bs_greeks, bs_price, implied_volatility


def test_call_price_matches_textbook_reference():
    # Hull, "Options, Futures, and Other Derivatives": S=42, K=40, r=0.10,
    # sigma=0.20, T=0.5 -> c ~= 4.76, p ~= 0.81
    call = bs_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, option_type="call")
    put = bs_price(S=42, K=40, T=0.5, r=0.10, sigma=0.20, option_type="put")
    assert call == pytest.approx(4.76, abs=0.01)
    assert put == pytest.approx(0.81, abs=0.01)


@pytest.mark.parametrize(
    "S,K,T,r,sigma",
    [
        (100, 100, 1.0, 0.05, 0.25),
        (150, 120, 0.25, 0.03, 0.40),
        (50, 60, 2.0, 0.045, 0.60),
        (355.74, 350, 30 / 365, 0.043, 0.30),
    ],
)
def test_put_call_parity(S, K, T, r, sigma):
    call = bs_price(S, K, T, r, sigma, "call")
    put = bs_price(S, K, T, r, sigma, "put")
    # C - P = S - K*exp(-rT)
    assert (call - put) == pytest.approx(S - K * math.exp(-r * T), abs=1e-6)


@pytest.mark.parametrize(
    "S,K,T,r,sigma,option_type",
    [
        (100, 100, 1.0, 0.05, 0.25, "call"),
        (100, 100, 1.0, 0.05, 0.25, "put"),
        (150, 120, 0.25, 0.03, 0.40, "call"),
        (50, 60, 2.0, 0.045, 0.60, "put"),
    ],
)
def test_implied_volatility_round_trips(S, K, T, r, sigma, option_type):
    price = bs_price(S, K, T, r, sigma, option_type)
    solved = implied_volatility(price, S, K, T, r, option_type)
    assert solved == pytest.approx(sigma, abs=1e-4)


def test_call_delta_between_zero_and_one():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.25, option_type="call")
    assert 0 < g["delta"] < 1


def test_put_delta_between_minus_one_and_zero():
    g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.25, option_type="put")
    assert -1 < g["delta"] < 0


def test_gamma_matches_between_call_and_put():
    call_g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.25, option_type="call")
    put_g = bs_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.25, option_type="put")
    assert call_g["gamma"] == pytest.approx(put_g["gamma"], abs=1e-9)
    assert call_g["vega"] == pytest.approx(put_g["vega"], abs=1e-9)


def test_deep_itm_call_delta_near_one():
    g = bs_greeks(S=200, K=50, T=1.0, r=0.05, sigma=0.20, option_type="call")
    assert g["delta"] > 0.98


def test_zero_dte_does_not_crash():
    # 0DTE: T denominator guarded, should return a finite price/greeks, not NaN/inf.
    price = bs_price(S=100, K=100, T=0.0, r=0.05, sigma=0.25, option_type="call")
    g = bs_greeks(S=100, K=100, T=0.0, r=0.05, sigma=0.25, option_type="call")
    assert math.isfinite(price)
    assert all(math.isfinite(v) for v in g.values())


def test_implied_volatility_raises_below_intrinsic():
    # A price below intrinsic value has no valid implied vol.
    with pytest.raises(ValueError):
        implied_volatility(market_price=0.01, S=200, K=50, T=1.0, r=0.05, option_type="call")
