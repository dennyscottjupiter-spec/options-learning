"""
The four strategies this project teaches, each reduced to the same shape: one
option contract (100 shares/contract) against the underlying, a payoff
function of terminal price, max profit/loss, breakeven, and capital required.

payoff_fn(S_T) returns *net* P&L in dollars (positive = profit) for the whole
position — for covered call and protective put that includes the 100 shares
already held, not just the option leg, since the point of both strategies is
what they do to a position you already own.

All four are constructed here as bullish-or-neutral-bullish payoff shapes
(profit region is S_T > breakeven), so pop_direction is 'above' on all of
them — that's a property of *these* four strategies, not a law, so it's
stored explicitly rather than assumed elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np

CONTRACT_MULTIPLIER = 100


@dataclass
class StrategyResult:
    name: str
    strategy_type: str
    contract_symbol: str
    option_type: Literal["call", "put"]
    strike: float
    expiration: str
    premium: float
    underlying_price: float
    max_profit: float | None  # None = unbounded upside
    max_loss: float  # signed worst-case P&L (negative)
    breakeven: list[float]
    capital_required: float
    payoff_fn: Callable[[np.ndarray], np.ndarray]
    pop_direction: Literal["above", "below"]


def build_long_call(contract: dict, underlying_price: float) -> StrategyResult:
    """Buy 1 call. The LEAPS play: own the right to buy the stock at today's
    price for months or years, paying only the premium instead of full share
    cost — the whole point of the 'acquire it cheaper later' thesis."""
    K = contract["strike"]
    premium = contract["ask"]  # buying, so you pay the ask

    def payoff_fn(S_T: np.ndarray) -> np.ndarray:
        return np.maximum(S_T - K, 0) * CONTRACT_MULTIPLIER - premium * CONTRACT_MULTIPLIER

    return StrategyResult(
        name="Long Call",
        strategy_type="long_call",
        contract_symbol=contract["symbol"],
        option_type="call",
        strike=K,
        expiration=contract["expiration"],
        premium=premium,
        underlying_price=underlying_price,
        max_profit=None,
        max_loss=-premium * CONTRACT_MULTIPLIER,
        breakeven=[K + premium],
        capital_required=premium * CONTRACT_MULTIPLIER,
        payoff_fn=payoff_fn,
        pop_direction="above",
    )


def build_cash_secured_put(contract: dict, underlying_price: float) -> StrategyResult:
    """Sell 1 put, with the strike's full cash value set aside to cover
    assignment. Earns premium now; worst case, you buy the stock at the
    strike — a price you chose because you'd be happy to own it there."""
    K = contract["strike"]
    premium = contract["bid"]  # selling, so you receive the bid

    def payoff_fn(S_T: np.ndarray) -> np.ndarray:
        return premium * CONTRACT_MULTIPLIER - np.maximum(K - S_T, 0) * CONTRACT_MULTIPLIER

    return StrategyResult(
        name="Cash-Secured Put",
        strategy_type="cash_secured_put",
        contract_symbol=contract["symbol"],
        option_type="put",
        strike=K,
        expiration=contract["expiration"],
        premium=premium,
        underlying_price=underlying_price,
        max_profit=premium * CONTRACT_MULTIPLIER,
        max_loss=premium * CONTRACT_MULTIPLIER - K * CONTRACT_MULTIPLIER,
        breakeven=[K - premium],
        capital_required=K * CONTRACT_MULTIPLIER,
        payoff_fn=payoff_fn,
        pop_direction="above",
    )


def build_covered_call(contract: dict, underlying_price: float) -> StrategyResult:
    """Sell 1 call against 100 shares you already own. Earns premium on stock
    that would otherwise just sit there; caps upside at the strike if called
    away. Net P&L is measured against today's stock value, since the shares
    are the asset actually at risk, not new capital."""
    K = contract["strike"]
    premium = contract["bid"]
    S0 = underlying_price

    def payoff_fn(S_T: np.ndarray) -> np.ndarray:
        return (np.minimum(S_T, K) - S0) * CONTRACT_MULTIPLIER + premium * CONTRACT_MULTIPLIER

    return StrategyResult(
        name="Covered Call",
        strategy_type="covered_call",
        contract_symbol=contract["symbol"],
        option_type="call",
        strike=K,
        expiration=contract["expiration"],
        premium=premium,
        underlying_price=S0,
        max_profit=(K - S0) * CONTRACT_MULTIPLIER + premium * CONTRACT_MULTIPLIER,
        max_loss=-S0 * CONTRACT_MULTIPLIER + premium * CONTRACT_MULTIPLIER,
        breakeven=[S0 - premium],
        capital_required=S0 * CONTRACT_MULTIPLIER,
        payoff_fn=payoff_fn,
        pop_direction="above",
    )


def build_protective_put(contract: dict, underlying_price: float) -> StrategyResult:
    """Buy 1 put against 100 shares you already own — insurance with a floor
    at the strike. Upside stays uncapped; you've just paid a premium for a
    guaranteed worst-case sale price."""
    K = contract["strike"]
    premium = contract["ask"]
    S0 = underlying_price

    def payoff_fn(S_T: np.ndarray) -> np.ndarray:
        return (np.maximum(S_T, K) - S0) * CONTRACT_MULTIPLIER - premium * CONTRACT_MULTIPLIER

    return StrategyResult(
        name="Protective Put",
        strategy_type="protective_put",
        contract_symbol=contract["symbol"],
        option_type="put",
        strike=K,
        expiration=contract["expiration"],
        premium=premium,
        underlying_price=S0,
        max_profit=None,
        max_loss=(K - S0) * CONTRACT_MULTIPLIER - premium * CONTRACT_MULTIPLIER,
        breakeven=[S0 + premium],
        capital_required=premium * CONTRACT_MULTIPLIER,
        payoff_fn=payoff_fn,
        pop_direction="above",
    )
