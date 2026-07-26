"""
Black-Scholes pricing, Greeks, and an implied-volatility solver.

This is the local fallback whenever Alpaca returns no Greeks/IV for a contract
— which happens on any zero bid/ask and always on same-day expirations (DTE is
a denominator; 0DTE divides by zero). Every value computed here should be
labelled "calculated locally" by the report, since it's an estimate from our
own model, not the market's.

Greek conventions (matching what Alpaca's own snapshot data returns, verified
against a live V options chain): theta is per calendar day, vega is per 1
percentage point of volatility (e.g. 20% -> 21%), rho is per 1 percentage
point of interest rate. Delta and gamma are unscaled.
"""
from __future__ import annotations

import math
from typing import Literal

from scipy.optimize import brentq
from scipy.stats import norm

OptionType = Literal["call", "put"]

_MIN_T = 1e-6  # avoid division by zero on 0DTE; treat as a few seconds to expiry


def d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    T = max(T, _MIN_T)
    sigma = max(sigma, 1e-6)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_price(S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType) -> float:
    """Black-Scholes price of a European call or put. T in years."""
    T = max(T, _MIN_T)
    d1, d2 = d1_d2(S, K, T, r, sigma)
    if option_type == "call":
        return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bs_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType) -> dict:
    """Returns {delta, gamma, theta, vega, rho} using the conventions documented
    at the top of this module."""
    T = max(T, _MIN_T)
    sigma = max(sigma, 1e-6)
    d1, d2 = d1_d2(S, K, T, r, sigma)
    phi_d1 = norm.pdf(d1)
    sqrt_T = math.sqrt(T)
    disc = math.exp(-r * T)

    gamma = phi_d1 / (S * sigma * sqrt_T)
    vega = (S * phi_d1 * sqrt_T) / 100.0

    if option_type == "call":
        delta = norm.cdf(d1)
        theta_year = -(S * phi_d1 * sigma) / (2 * sqrt_T) - r * K * disc * norm.cdf(d2)
        rho = (K * T * disc * norm.cdf(d2)) / 100.0
    else:
        delta = norm.cdf(d1) - 1.0
        theta_year = -(S * phi_d1 * sigma) / (2 * sqrt_T) + r * K * disc * norm.cdf(-d2)
        rho = -(K * T * disc * norm.cdf(-d2)) / 100.0

    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta_year / 365.0,
        "vega": vega,
        "rho": rho,
    }


def implied_volatility(
    market_price: float, S: float, K: float, T: float, r: float, option_type: OptionType
) -> float:
    """Solves for the sigma that reproduces `market_price`, via Brent's method.
    Raises ValueError if market_price is outside the range Black-Scholes can
    produce for any sigma in (1e-6, 5.0) — e.g. below intrinsic value."""
    T = max(T, _MIN_T)

    def f(sigma: float) -> float:
        return bs_price(S, K, T, r, sigma, option_type) - market_price

    lo, hi = 1e-6, 5.0
    if f(lo) * f(hi) > 0:
        raise ValueError(
            f"No implied volatility in [{lo}, {hi}] reproduces price {market_price} "
            f"for S={S} K={K} T={T} r={r} {option_type}"
        )
    return brentq(f, lo, hi, xtol=1e-8)
