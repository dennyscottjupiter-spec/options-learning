"""
Probability of profit: two independent engines that should agree.

1. Closed-form — under the lognormal terminal-price assumption, P(S_T > X) =
   N(d2) evaluated at the strategy's breakeven (not its strike; conflating the
   two is a common beginner mistake this project deliberately avoids).
2. Monte Carlo — simulates full price paths (not just terminal prices) under
   geometric Brownian motion, with antithetic variates and a fixed seed so
   results are reproducible run-to-run. This also yields probability-of-touch
   (the odds price merely reaches a barrier before expiry) and lets
   strategies.py compute conditional average win/loss from the same paths.

If the two POP engines disagree by more than the configured threshold, that
gap itself is a signal the lognormal assumption is straining — the report
surfaces it rather than picking one number silently.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.stats import norm

from optionslab.bs import d1_d2

Direction = Literal["above", "below"]
TouchDirection = Literal["up", "down"]

_MIN_T = 1e-6
_MAX_STEPS = 504  # ~2 trading years at daily granularity, caps cost for LEAPS


def probability_of_profit_closed_form(
    S: float, breakeven: float, T: float, r: float, sigma: float, direction: Direction
) -> float:
    """P(S_T > breakeven) if direction='above' (long-call-shaped profit region),
    or P(S_T < breakeven) if direction='below' (long-put-shaped)."""
    T = max(T, _MIN_T)
    _, d2 = d1_d2(S, breakeven, T, r, sigma)
    return float(norm.cdf(d2) if direction == "above" else norm.cdf(-d2))


def simulate_paths(
    S: float,
    T: float,
    r: float,
    sigma: float,
    n_paths: int = 100_000,
    seed: int = 7,
) -> np.ndarray:
    """Simulates GBM price paths under the risk-neutral measure. Returns an
    array of shape (n_paths, n_steps + 1), column 0 = S, last column = terminal
    price. Uses antithetic variates (mirrored Z draws) so the estimate is less
    noisy at a given path count, and a fixed seed for reproducibility."""
    T = max(T, _MIN_T)
    n_steps = min(_MAX_STEPS, max(10, round(T * 252)))
    dt = T / n_steps

    rng = np.random.default_rng(seed)
    half = (n_paths + 1) // 2
    z = rng.standard_normal((half, n_steps))
    z = np.concatenate([z, -z], axis=0)[:n_paths]

    drift = (r - 0.5 * sigma**2) * dt
    diffusion = sigma * np.sqrt(dt) * z
    log_returns = drift + diffusion

    log_paths = np.cumsum(log_returns, axis=1)
    paths = S * np.exp(log_paths)
    paths = np.concatenate([np.full((n_paths, 1), S), paths], axis=1)
    return paths


def probability_of_profit_monte_carlo(
    terminal_prices: np.ndarray, breakeven: float, direction: Direction
) -> float:
    if direction == "above":
        return float(np.mean(terminal_prices > breakeven))
    return float(np.mean(terminal_prices < breakeven))


def probability_of_touch(paths: np.ndarray, barrier: float, direction: TouchDirection) -> float:
    """Odds the price reaches `barrier` at any point before expiry — often the
    number that actually matters more than terminal POP for short-dated trades."""
    if direction == "up":
        touched = np.any(paths >= barrier, axis=1)
    else:
        touched = np.any(paths <= barrier, axis=1)
    return float(np.mean(touched))
