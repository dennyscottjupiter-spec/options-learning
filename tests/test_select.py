"""
Covers the selection pipeline with no network access: `market` is stubbed out
so the chain, spot price, and account are all deterministic fixtures (see
tests/conftest.py).

Monte Carlo path counts are also cut down here (see `patched_config`) — the
selection logic under test is path-count-independent, and the real 100,000
paths would allocate hundreds of MB per contract for no extra confidence.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from optionslab import market, select
from optionslab.config import load_config

from conftest import RATE, SIGMA, SPOT, _contract

# --- expiration windows -----------------------------------------------------


def test_long_call_window_is_the_leaps_window():
    cfg = load_config()["strategies"]
    today = date(2026, 1, 1)
    lo, hi = select.default_expiration_window("long_call", today)

    assert lo == (today + timedelta(days=cfg["leaps_min_dte"])).isoformat()
    assert hi == (today + timedelta(days=cfg["leaps_max_dte"])).isoformat()


def test_premium_strategies_share_the_short_dated_window():
    today = date(2026, 1, 1)
    csp = select.default_expiration_window("cash_secured_put", today)
    cc = select.default_expiration_window("covered_call", today)

    assert csp == cc
    assert csp != select.default_expiration_window("long_call", today)


def test_protective_put_window_is_not_the_premium_window():
    """It tracks the intended holding period, not a premium-selling cycle."""
    today = date(2026, 1, 1)
    assert select.default_expiration_window("protective_put", today) != select.default_expiration_window(
        "covered_call", today
    )


# --- liquidity gate ---------------------------------------------------------


def test_healthy_quote_passes_liquidity(leaps_expiration: str):
    assert select.passes_liquidity(_contract(100.0, "call", leaps_expiration)) is True


def test_missing_quote_fails_liquidity(leaps_expiration: str):
    assert select.passes_liquidity(_contract(100.0, "call", leaps_expiration, quoted=False)) is False


def test_wide_spread_fails_liquidity(leaps_expiration: str):
    contract = _contract(100.0, "call", leaps_expiration)
    mid = (contract["bid"] + contract["ask"]) / 2
    # 40% spread, far past the 10% ceiling in config.toml
    contract["bid"], contract["ask"] = mid * 0.8, mid * 1.2
    assert select.passes_liquidity(contract) is False


def test_thin_quoted_depth_fails_liquidity(leaps_expiration: str):
    contract = _contract(100.0, "call", leaps_expiration)
    contract["bid_size"], contract["ask_size"] = 1, 1
    assert select.passes_liquidity(contract) is False


# --- enrichment -------------------------------------------------------------


def test_missing_greeks_are_calculated_locally_and_labelled(leaps_expiration: str):
    enriched = select.enrich_contract(_contract(100.0, "call", leaps_expiration), SPOT, RATE)

    assert enriched["greeks_source"] == "calculated locally"
    # Priced off SIGMA, so the solver must recover roughly that IV back.
    assert enriched["implied_volatility"] == pytest.approx(SIGMA, abs=0.02)
    # ATM call delta sits near 0.5 (a little above, thanks to drift over a year).
    assert 0.5 < enriched["delta"] < 0.75


def test_alpaca_greeks_are_kept_and_labelled(leaps_expiration: str):
    contract = _contract(100.0, "call", leaps_expiration)
    contract["delta"] = 0.42
    contract["implied_volatility"] = 0.99

    enriched = select.enrich_contract(contract, SPOT, RATE)

    assert enriched["greeks_source"] == "alpaca"
    assert enriched["delta"] == 0.42          # untouched
    assert enriched["implied_volatility"] == 0.99


def test_unquoted_contract_is_dropped(leaps_expiration: str):
    contract = _contract(100.0, "call", leaps_expiration, quoted=False)
    assert select.enrich_contract(contract, SPOT, RATE) is None


def test_price_below_intrinsic_is_dropped(leaps_expiration: str):
    """No sigma reproduces it, so Black-Scholes can't explain the quote."""
    contract = _contract(60.0, "call", leaps_expiration)
    contract["bid"], contract["ask"] = 1.0, 1.1  # deep ITM but priced like a lottery ticket
    assert select.enrich_contract(contract, SPOT, RATE) is None


# --- evaluation -------------------------------------------------------------


def test_evaluate_contract_reports_agreeing_pop_engines(patched_config, leaps_expiration: str):
    contract = select.enrich_contract(_contract(90.0, "call", leaps_expiration), SPOT, RATE)
    result = select.evaluate_contract(contract, "long_call", SPOT, RATE, 20_000, 7)

    assert 0.0 <= result["pop_closed_form"] <= 1.0
    assert result["pop_monte_carlo"] == pytest.approx(result["pop_closed_form"], abs=0.02)
    assert result["pop_disagreement_flag"] is False
    # A long call's breakeven is above spot, so touching it is at least as
    # likely as finishing above it.
    assert result["probability_of_touch"] >= result["pop_monte_carlo"]
    assert result["avg_win"] > 0 and result["avg_loss"] > 0
    assert result["liquidity_ok"] is True


def test_evaluate_contract_is_reproducible(patched_config, leaps_expiration: str):
    contract = select.enrich_contract(_contract(90.0, "call", leaps_expiration), SPOT, RATE)
    args = (contract, "long_call", SPOT, RATE, 5_000, 7)

    assert select.evaluate_contract(*args)["score"] == select.evaluate_contract(*args)["score"]


# --- full pipeline ----------------------------------------------------------


def test_select_best_picks_from_the_target_delta_band(patched_config, stub_market, call_chain):
    """The target delta narrows the *candidate band*; the winner inside that
    band is then chosen by score, so it need not be the closest to 0.75."""
    result = select.select_best("TST", "long_call")

    assert result["ticker"] == "TST"
    assert result["spot_price"] == SPOT
    assert result["target_delta"] == 0.75
    assert result["candidates_evaluated"] == 12  # only the band is evaluated
    assert result["best"]["contract"]["type"] == "call"

    enriched = [select.enrich_contract(c, SPOT, RATE) for c in call_chain]
    band = sorted(enriched, key=lambda c: abs(c["delta"] - 0.75))[:12]
    assert result["best"]["contract"]["symbol"] in {c["symbol"] for c in band}


def test_select_best_explains_why_it_beat_the_runner_up(patched_config, stub_market):
    result = select.select_best("TST", "long_call")
    why = result["why_best_data"]

    assert result["runner_up"] is not None
    assert why["best_symbol"] != why["runner_up_symbol"]
    assert why["best_score"] >= why["runner_up_score"]
    assert why["margin"] == pytest.approx(why["best_score"] - why["runner_up_score"])


def test_select_best_flags_unaffordable_positions(
    patched_config, stub_market, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        market,
        "get_account",
        lambda: {"status": "ACTIVE", "cash": 1.0, "buying_power": 1.0, "portfolio_value": 1.0},
    )
    result = select.select_best("TST", "long_call")

    assert result["best"]["affordable"] is False


def test_select_best_raises_when_the_chain_has_no_matching_type(
    patched_config, monkeypatch: pytest.MonkeyPatch, leaps_expiration: str
):
    puts_only = [_contract(k, "put", leaps_expiration) for k in range(80, 121, 5)]
    monkeypatch.setattr(market, "get_latest_price", lambda ticker: SPOT)
    monkeypatch.setattr(market, "get_option_chain", lambda ticker, **kwargs: puts_only)

    with pytest.raises(ValueError, match="No usable call contracts"):
        select.select_best("TST", "long_call")
