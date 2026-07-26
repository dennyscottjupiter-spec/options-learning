"""
Ties the data layer, math engine, and strategies together: picks an
expiration window (strategy-specific default, or a manual override date),
filters the chain to that window, fills in local Greeks/IV where Alpaca has
none, narrows to strikes near the strategy's target delta, evaluates every
candidate (POP, probability of touch, avg win/loss, risk-adjusted score),
and returns the top pick with a one-line explanation of why it beat #2.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal

from optionslab import market
from optionslab.bs import bs_greeks, implied_volatility
from optionslab.config import load_config
from optionslab.pop import (
    probability_of_profit_closed_form,
    probability_of_profit_monte_carlo,
    probability_of_touch,
    simulate_paths,
)
from optionslab.strategies import (
    build_cash_secured_put,
    build_covered_call,
    build_long_call,
    build_protective_put,
)

StrategyType = Literal["long_call", "cash_secured_put", "covered_call", "protective_put"]

_OPTION_TYPE: dict[StrategyType, str] = {
    "long_call": "call",
    "cash_secured_put": "put",
    "covered_call": "call",
    "protective_put": "put",
}

# Best-practice starting point per strategy. The report always explains why
# this delta/window was picked — that explanation is the lesson.
_TARGET_DELTA: dict[StrategyType, float] = {
    "long_call": 0.75,       # deep-ish ITM: behaves like a leveraged stock substitute
    "cash_secured_put": -0.30,  # classic premium/assignment-odds balance
    "covered_call": 0.30,    # classic premium vs upside-given-up balance
    "protective_put": -0.30,
}

_BUILDER = {
    "long_call": build_long_call,
    "cash_secured_put": build_cash_secured_put,
    "covered_call": build_covered_call,
    "protective_put": build_protective_put,
}

_CANDIDATE_BAND = 12  # closest N strikes by delta distance to evaluate fully


def default_expiration_window(strategy_type: StrategyType, today: date | None = None) -> tuple[str, str]:
    cfg = load_config()["strategies"]
    today = today or date.today()
    if strategy_type == "long_call":
        lo, hi = cfg["leaps_min_dte"], cfg["leaps_max_dte"]
    elif strategy_type == "protective_put":
        # No fixed best-practice window like the premium-selling strategies —
        # duration should track how long you plan to hold the stock. 60-120
        # DTE is a reasonable default (roughly one earnings cycle of cover);
        # pass expiration_date to select_best() for a specific holding period.
        lo, hi = 60, 120
    else:
        lo, hi = cfg["premium_min_dte"], cfg["premium_max_dte"]
    return (
        (today + timedelta(days=lo)).isoformat(),
        (today + timedelta(days=hi)).isoformat(),
    )


def passes_liquidity(contract: dict) -> bool:
    """Warned on, never silently hidden — the caller still gets the contract,
    just flagged. Judges quoted depth and spread since Alpaca has no
    open-interest field to filter on."""
    cfg = load_config()["liquidity"]
    bid, ask = contract.get("bid"), contract.get("ask")
    if not bid or not ask or bid <= 0 or ask <= 0:
        return False
    mid = (bid + ask) / 2
    spread_pct = (ask - bid) / mid if mid > 0 else float("inf")
    if spread_pct > cfg["max_bid_ask_spread_pct"]:
        return False
    bid_size, ask_size = contract.get("bid_size") or 0, contract.get("ask_size") or 0
    if bid_size < cfg["min_quote_size"] or ask_size < cfg["min_quote_size"]:
        return False
    return True


def enrich_contract(contract: dict, S: float, r: float) -> dict | None:
    """Fills missing delta/gamma/theta/vega/rho/IV via local Black-Scholes,
    tagging the source so the report can label it 'calculated locally'.
    Returns None if there's no price at all to solve from (fully unusable)."""
    bid, ask = contract.get("bid"), contract.get("ask")
    if not bid and not ask:
        return None

    contract = dict(contract)
    exp = datetime.strptime(contract["expiration"], "%Y-%m-%d").date()
    T = max((exp - date.today()).days, 0) / 365.0

    if contract.get("delta") is None:
        mid = ((bid or 0) + (ask or 0)) / 2 or (ask or bid)
        try:
            iv = implied_volatility(mid, S, contract["strike"], T, r, contract["type"])
            greeks = bs_greeks(S, contract["strike"], T, r, iv, contract["type"])
        except ValueError:
            return None  # price outside what Black-Scholes can explain (e.g. below intrinsic)
        contract.update(greeks)
        contract["implied_volatility"] = iv
        contract["greeks_source"] = "calculated locally"
    else:
        contract["greeks_source"] = "alpaca"
    return contract


def evaluate_contract(
    contract: dict, strategy_type: StrategyType, S: float, r: float, mc_paths: int, mc_seed: int
) -> dict:
    strat = _BUILDER[strategy_type](contract, S)
    exp = datetime.strptime(contract["expiration"], "%Y-%m-%d").date()
    dte = max((exp - date.today()).days, 1)
    T = dte / 365.0
    sigma = contract.get("implied_volatility") or 0.0
    breakeven = strat.breakeven[0]

    pop_cf = probability_of_profit_closed_form(S, breakeven, T, r, sigma, strat.pop_direction)
    paths = simulate_paths(S, T, r, sigma, n_paths=mc_paths, seed=mc_seed)
    terminal = paths[:, -1]
    pop_mc = probability_of_profit_monte_carlo(terminal, breakeven, strat.pop_direction)
    touch_direction = "up" if breakeven > S else "down"
    touch_prob = probability_of_touch(paths, breakeven, touch_direction)

    payoffs = strat.payoff_fn(terminal)
    wins = payoffs[payoffs > 0]
    losses = payoffs[payoffs <= 0]
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(-losses.mean()) if len(losses) else 0.0

    score = 0.0
    if strat.capital_required > 0:
        score = (pop_mc * avg_win - (1 - pop_mc) * avg_loss) / strat.capital_required * (365 / dte)

    disagreement_pp = abs(pop_cf - pop_mc) * 100
    flag_threshold = load_config()["math"]["pop_disagreement_flag_pp"]

    return {
        "strategy": strat,
        "contract": contract,
        "dte": dte,
        "pop_closed_form": pop_cf,
        "pop_monte_carlo": pop_mc,
        "pop_disagreement_pp": disagreement_pp,
        "pop_disagreement_flag": disagreement_pp > flag_threshold,
        "probability_of_touch": touch_prob,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "score": score,
        "liquidity_ok": passes_liquidity(contract),
    }


def select_best(
    ticker: str,
    strategy_type: StrategyType,
    expiration_date: str | None = None,
) -> dict:
    """Full pipeline for one ticker + strategy. Pass `expiration_date` (an
    exact date) to override the strategy's best-practice default window."""
    cfg = load_config()
    S = market.get_latest_price(ticker)
    r = cfg["math"]["risk_free_rate"]
    mc_paths = cfg["math"]["monte_carlo_paths"]
    mc_seed = cfg["math"]["monte_carlo_seed"]
    option_type = _OPTION_TYPE[strategy_type]
    target_delta = _TARGET_DELTA[strategy_type]

    if expiration_date:
        chain = market.get_option_chain(ticker, expiration_date=expiration_date)
    else:
        lo, hi = default_expiration_window(strategy_type)
        chain = market.get_option_chain(ticker, expiration_date_gte=lo, expiration_date_lte=hi)

    candidates = [c for c in chain if c["type"] == option_type]
    enriched = [c for c in (enrich_contract(c, S, r) for c in candidates) if c is not None]

    if not enriched:
        raise ValueError(f"No usable {option_type} contracts found for {ticker} in the target window.")

    enriched.sort(key=lambda c: abs((c["delta"] or 0) - target_delta))
    band = enriched[:_CANDIDATE_BAND]

    # Two-phase evaluation: a cheap screening pass (small path count) ranks
    # the whole band fast, then only the top 2 get the full-precision
    # simulation the report actually shows. On a dozen candidates this is the
    # difference between ~12 full Monte Carlo runs and ~2 — the screening
    # pass is noisier but score ordering is stable enough to trust for
    # picking who's worth simulating precisely.
    screen_paths = min(mc_paths, 5_000)
    screened = [evaluate_contract(c, strategy_type, S, r, screen_paths, mc_seed) for c in band]
    screened.sort(key=lambda e: e["score"], reverse=True)

    top_contracts = [e["contract"] for e in screened[:2]]
    evaluated = [evaluate_contract(c, strategy_type, S, r, mc_paths, mc_seed) for c in top_contracts]
    evaluated.sort(key=lambda e: e["score"], reverse=True)

    account = market.get_account()
    best = evaluated[0]
    best["affordable"] = best["strategy"].capital_required <= account["buying_power"]

    runner_up = evaluated[1] if len(evaluated) > 1 else None
    # Raw comparison numbers, not a formatted sentence — this module has no
    # i18n knowledge; report.py fills the localized "why #1 beat #2" template.
    why_best_data = None
    if runner_up:
        why_best_data = {
            "best_symbol": best["contract"]["symbol"],
            "best_strike": best["strategy"].strike,
            "best_score": best["score"],
            "runner_up_symbol": runner_up["contract"]["symbol"],
            "runner_up_strike": runner_up["strategy"].strike,
            "runner_up_score": runner_up["score"],
            "margin": best["score"] - runner_up["score"],
        }

    return {
        "ticker": ticker,
        "spot_price": S,
        "strategy_type": strategy_type,
        "target_delta": target_delta,
        "best": best,
        "runner_up": runner_up,
        "why_best_data": why_best_data,
        "candidates_evaluated": len(screened),
        "account": account,
    }
