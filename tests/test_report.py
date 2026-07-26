"""
Covers report.build_report_context / render_report_html with no network
access: select.py runs for real against the synthetic chain from conftest.py,
and only the two extra seams report.py touches beyond select.py (daily bars,
fundamentals) are stubbed. This exercises the actual dict shape select.py
produces instead of a hand-built fixture that would drift from it.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from markupsafe import escape

from optionslab import fundamentals, market, report
from optionslab.i18n import CATALOG
from optionslab.strategies import build_covered_call

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# --- transparency: no local path leaks into the published static export ----


def test_static_export_uses_repo_relative_src_dir(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=True)

    assert ctx["src_dir"] == "src/optionslab"
    assert "C:" not in ctx["src_dir"]
    assert "usuario" not in ctx["src_dir"]
    for row in ctx["methodology"]:
        assert "C:" not in row["source"]
        assert "usuario" not in row["source"]


def test_live_app_uses_absolute_src_dir(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=False)

    assert ctx["src_dir"] == str(PROJECT_ROOT / "src" / "optionslab").replace("\\", "/")


# --- methodology table stays wired to real source files ---------------------


def test_methodology_sources_resolve_to_real_files(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=False)

    assert len(ctx["methodology"]) > 0
    for row in ctx["methodology"]:
        # "path/to/file.py::func" or "a.py::f -> b.py::g" — check every *.py
        # segment named in `source` actually exists on disk.
        for token in row["source"].replace("→", " ").split():
            if token.endswith(".py") or "::" in token:
                file_part = token.split("::")[0]
                if file_part.endswith(".py"):
                    assert Path(file_part).is_file(), f"missing source file: {file_part}"


# --- i18n: templates branch on mode, never language -------------------------


def test_lang_changes_prose_but_not_numbers(patched_config, stub_market, stub_report_data):
    ctx_en = report.build_report_context("TST", "long_call", lang="en", static_export=True)
    ctx_pt = report.build_report_context("TST", "long_call", lang="pt-BR", static_export=True)

    assert ctx_en["s"]["strike"] == ctx_pt["s"]["strike"] == "Strike"  # both catalogs use it verbatim
    assert ctx_en["s"]["breakeven"] != ctx_pt["s"]["breakeven"]

    assert ctx_en["spot_price"] == ctx_pt["spot_price"]
    assert ctx_en["best"]["contract"]["symbol"] == ctx_pt["best"]["contract"]["symbol"]
    assert ctx_en["candidates_evaluated"] == ctx_pt["candidates_evaluated"]


@pytest.mark.parametrize("lang", ["en", "pt-BR"])
def test_why_best_template_formats_without_error(patched_config, stub_market, stub_report_data, lang):
    ctx = report.build_report_context("TST", "long_call", lang=lang, static_export=True)

    assert ctx["why_best"]
    for placeholder in ("best_symbol", "best_strike", "best_score", "runner_up_symbol", "margin"):
        assert "{" + placeholder not in ctx["why_best"]  # every field actually substituted


def test_every_catalog_key_present_in_both_languages():
    """A key added to one language's CATALOG dict but not the other would
    KeyError only at render time for whichever lang is missing it."""
    en_keys = set(CATALOG["en"])
    pt_keys = set(CATALOG["pt-BR"])
    assert en_keys == pt_keys


# --- earnings warning: date-window logic ------------------------------------


def test_earnings_warning_true_when_earnings_falls_inside_expiration_window(
    patched_config, stub_market, monkeypatch: pytest.MonkeyPatch, daily_bars
):
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": symbol,
            "market_cap": None,
            "sector": None,
            "next_earnings_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["earnings_warning"] is True


def test_earnings_warning_false_when_earnings_is_after_expiration(
    patched_config, stub_market, monkeypatch: pytest.MonkeyPatch, daily_bars
):
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": symbol,
            "market_cap": None,
            "sector": None,
            "next_earnings_date": (date.today() + timedelta(days=1000)).isoformat(),
        },
    )
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["earnings_warning"] is False


def test_earnings_warning_false_when_no_earnings_date_on_file(
    patched_config, stub_market, stub_report_data
):
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["earnings_warning"] is False


# --- early-assignment warning: ITM short leg + ex-dividend inside window ----


@pytest.mark.parametrize(
    "strategy_type,option_type,strike,spot,expected",
    [
        ("covered_call", "call", 100.0, 110.0, True),  # ITM short call
        ("covered_call", "call", 100.0, 90.0, False),  # OTM short call
        ("cash_secured_put", "put", 100.0, 90.0, True),  # ITM short put
        ("cash_secured_put", "put", 100.0, 110.0, False),  # OTM short put
        ("long_call", "call", 100.0, 110.0, False),  # never a short option
        ("protective_put", "put", 100.0, 90.0, False),  # never a short option
    ],
)
def test_early_assignment_warning_gated_on_strategy_and_moneyness(
    strategy_type, option_type, strike, spot, expected
):
    exp_date = date.today() + timedelta(days=35)
    ex_dividend = (date.today() + timedelta(days=10)).isoformat()
    assert (
        report._early_assignment_warning(strategy_type, option_type, strike, spot, ex_dividend, exp_date)
        is expected
    )


def test_early_assignment_warning_false_when_ex_dividend_after_expiration():
    exp_date = date.today() + timedelta(days=35)
    ex_dividend = (date.today() + timedelta(days=100)).isoformat()
    assert report._early_assignment_warning("covered_call", "call", 100.0, 110.0, ex_dividend, exp_date) is False


def test_early_assignment_warning_false_when_no_ex_dividend_date():
    exp_date = date.today() + timedelta(days=35)
    assert report._early_assignment_warning("covered_call", "call", 100.0, 110.0, None, exp_date) is False


def _covered_call_chain(expiration: str, spot: float) -> list[dict]:
    """Calls priced at `spot` (not conftest._contract's fixed SPOT=100) so the
    synthetic chain stays internally consistent with the get_latest_price
    override below — pricing contracts at one spot while select.py evaluates
    them against another makes every quote look mispriced relative to
    intrinsic value and enrich_contract discards the whole chain."""
    from optionslab.bs import bs_price

    T = (date.fromisoformat(expiration) - date.today()).days / 365.0
    contracts = []
    for k in range(60, 141, 5):
        fair = float(bs_price(spot, k, T, 0.043, 0.30, "call"))
        contracts.append(
            {
                "symbol": f"TST{expiration.replace('-', '')}C{int(k * 1000):08d}",
                "underlying": "TST",
                "expiration": expiration,
                "type": "call",
                "strike": float(k),
                "bid": round(fair * 0.99, 2),
                "ask": round(fair * 1.01, 2),
                "bid_size": 10,
                "ask_size": 10,
                "last_price": round(fair, 2),
                "implied_volatility": None,
                "delta": None,
                "gamma": None,
                "theta": None,
                "vega": None,
                "rho": None,
            }
        )
    return contracts


def test_early_assignment_warning_true_end_to_end_for_itm_covered_call(
    patched_config, monkeypatch: pytest.MonkeyPatch, daily_bars
):
    expiration = (date.today() + timedelta(days=35)).isoformat()
    monkeypatch.setattr(market, "get_latest_price", lambda ticker: 200.0)  # ITM for every strike (max 140)
    monkeypatch.setattr(market, "get_option_chain", lambda ticker, **kwargs: _covered_call_chain(expiration, 200.0))
    monkeypatch.setattr(
        market,
        "get_account",
        lambda: {"status": "ACTIVE", "cash": 50_000.0, "buying_power": 50_000.0, "portfolio_value": 50_000.0},
    )
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": symbol,
            "market_cap": None,
            "sector": None,
            "next_earnings_date": None,
            "next_ex_dividend_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    ctx = report.build_report_context("TST", "covered_call", static_export=True)
    assert ctx["early_assignment_warning"] is True

    html = report.render_report_html("TST", "covered_call", mode="learn", lang="en", static_export=True, asset_prefix=".")
    assert CATALOG["en"]["early_assignment_warning_title"] in html


def test_early_assignment_warning_false_end_to_end_for_otm_covered_call(
    patched_config, monkeypatch: pytest.MonkeyPatch, daily_bars
):
    expiration = (date.today() + timedelta(days=35)).isoformat()
    monkeypatch.setattr(market, "get_latest_price", lambda ticker: 58.0)  # OTM for every strike (min 60)
    monkeypatch.setattr(market, "get_option_chain", lambda ticker, **kwargs: _covered_call_chain(expiration, 58.0))
    monkeypatch.setattr(
        market,
        "get_account",
        lambda: {"status": "ACTIVE", "cash": 50_000.0, "buying_power": 50_000.0, "portfolio_value": 50_000.0},
    )
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": symbol,
            "market_cap": None,
            "sector": None,
            "next_earnings_date": None,
            "next_ex_dividend_date": (date.today() + timedelta(days=10)).isoformat(),
        },
    )
    ctx = report.build_report_context("TST", "covered_call", static_export=True)
    assert ctx["early_assignment_warning"] is False


def test_early_assignment_warning_never_true_for_long_call(patched_config, stub_market, stub_report_data):
    """stub_report_data's fundamentals stub has no next_ex_dividend_date key at
    all (pre-dates this field) — build_report_context must tolerate that."""
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["early_assignment_warning"] is False


# --- premium split: intrinsic/extrinsic + moneyness -------------------------


@pytest.mark.parametrize(
    "spot,strike,premium,option_type,atm_band_pct,expected_intrinsic,expected_moneyness",
    [
        (110.0, 100.0, 12.0, "call", 0.02, 10.0, "itm"),  # call ITM: intrinsic=spot-strike
        (90.0, 100.0, 2.0, "call", 0.02, 0.0, "otm"),  # call OTM: intrinsic=0
        (100.5, 100.0, 3.0, "call", 0.02, 0.5, "atm"),  # within +/-2% band -> ATM despite tiny intrinsic
        (90.0, 100.0, 12.0, "put", 0.02, 10.0, "itm"),  # put ITM: intrinsic=strike-spot
        (110.0, 100.0, 2.0, "put", 0.02, 0.0, "otm"),  # put OTM: intrinsic=0
    ],
)
def test_moneyness_split_intrinsic_and_label(
    spot, strike, premium, option_type, atm_band_pct, expected_intrinsic, expected_moneyness
):
    result = report._moneyness_split(spot, strike, premium, option_type, atm_band_pct)
    assert result["intrinsic"] == pytest.approx(expected_intrinsic)
    assert result["extrinsic"] == pytest.approx(premium - expected_intrinsic)
    assert result["intrinsic"] + result["extrinsic"] == pytest.approx(premium)
    assert result["moneyness"] == expected_moneyness


def test_moneyness_split_bar_percentages_never_negative_or_over_100():
    """A quote priced slightly below intrinsic (narrow-spread edge case) would
    make extrinsic negative — the dollar figures should reflect that exactly,
    but the bar's width percentages must stay within [0, 100]."""
    result = report._moneyness_split(120.0, 100.0, 15.0, "call", 0.02)
    assert result["extrinsic"] == pytest.approx(-5.0)  # intrinsic (20) exceeds premium (15)
    assert 0.0 <= result["intrinsic_pct"] <= 100.0
    assert 0.0 <= result["extrinsic_pct"] <= 100.0
    assert result["intrinsic_pct"] + result["extrinsic_pct"] == pytest.approx(100.0)


def test_moneyness_split_wired_into_report_context(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    split = ctx["moneyness_split"]
    assert split["intrinsic"] + split["extrinsic"] == pytest.approx(ctx["strategy"].premium)
    assert split["moneyness"] in ("itm", "atm", "otm")

    html = report.render_report_html("TST", "long_call", mode="learn", lang="en", static_export=True, asset_prefix=".")
    assert 'class="moneyness-badge' in html
    assert 'class="premium-split-bar"' in html


# --- max profit/loss net of commissions + assignment tax note ---------------


def test_net_max_profit_and_loss_reflect_commission_config(
    patched_config, stub_market, stub_report_data, monkeypatch: pytest.MonkeyPatch
):
    patched_config["costs"]["commission_per_contract"] = 5.0
    monkeypatch.setattr(report, "load_config", lambda: patched_config)

    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["round_trip_commission"] == pytest.approx(10.0)
    assert ctx["net_max_profit"] is None  # long_call has unbounded upside
    assert ctx["net_max_loss"] == pytest.approx(ctx["strategy"].max_loss - 10.0)


def test_net_max_loss_changes_when_commission_config_changes(
    patched_config, stub_market, stub_report_data, monkeypatch: pytest.MonkeyPatch
):
    patched_config["costs"]["commission_per_contract"] = 0.10
    monkeypatch.setattr(report, "load_config", lambda: patched_config)
    ctx_cheap = report.build_report_context("TST", "long_call", static_export=True)

    patched_config["costs"]["commission_per_contract"] = 5.0
    ctx_expensive = report.build_report_context("TST", "long_call", static_export=True)

    assert ctx_cheap["net_max_loss"] != ctx_expensive["net_max_loss"]


def test_assignment_tax_note_only_for_covered_call(patched_config, monkeypatch: pytest.MonkeyPatch, daily_bars):
    expiration = (date.today() + timedelta(days=35)).isoformat()
    monkeypatch.setattr(market, "get_latest_price", lambda ticker: 105.0)
    monkeypatch.setattr(market, "get_option_chain", lambda ticker, **kwargs: _covered_call_chain(expiration, 105.0))
    monkeypatch.setattr(
        market,
        "get_account",
        lambda: {"status": "ACTIVE", "cash": 50_000.0, "buying_power": 50_000.0, "portfolio_value": 50_000.0},
    )
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": symbol,
            "market_cap": None,
            "sector": None,
            "next_earnings_date": None,
            "next_ex_dividend_date": None,
        },
    )
    html = report.render_report_html("TST", "covered_call", mode="pro", lang="en", static_export=True, asset_prefix=".")
    assert CATALOG["en"]["assignment_tax_note"] in html


def test_assignment_tax_note_absent_for_long_call(patched_config, stub_market, stub_report_data):
    html = report.render_report_html("TST", "long_call", mode="pro", lang="en", static_export=True, asset_prefix=".")
    assert CATALOG["en"]["assignment_tax_note"] not in html


# --- "What happens next": take-profit, theta decay, rolling -----------------


def test_take_profit_price_matches_closed_form_for_covered_call():
    """Below the strike, covered-call payoff is linear in S_T, so the price at
    which it reaches a target profit has a closed form to check the bisection
    helper against: payoff(S_T) = (S_T - S0 + premium) * 100 for S_T < K."""
    contract = {"symbol": "T", "strike": 110.0, "expiration": "2099-01-01", "bid": 4.0, "ask": 4.2}
    strat = build_covered_call(contract, underlying_price=100.0)
    target = strat.max_profit * 0.5

    price = report._take_profit_price(strat, target)

    expected = target / 100 - strat.premium + strat.underlying_price
    assert price == pytest.approx(expected, abs=0.01)
    assert strat.payoff_fn(np.array([price]))[0] == pytest.approx(target, abs=1.0)


def test_take_profit_none_for_unbounded_strategy(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["strategy"].max_profit is None
    assert ctx["take_profit_dollar"] is None
    assert ctx["take_profit_price"] is None


def test_theta_decay_svg_present_and_decays_to_zero(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["theta_decay_svg"].startswith("<svg")
    assert ctx["theta_decay_svg"].rstrip().endswith("</svg>")
    assert "$0.00" in ctx["theta_decay_svg"]  # extrinsic value at expiry


def test_rolling_explainer_only_for_covered_call(patched_config, monkeypatch: pytest.MonkeyPatch, daily_bars):
    expiration = (date.today() + timedelta(days=35)).isoformat()
    monkeypatch.setattr(market, "get_latest_price", lambda ticker: 105.0)
    monkeypatch.setattr(market, "get_option_chain", lambda ticker, **kwargs: _covered_call_chain(expiration, 105.0))
    monkeypatch.setattr(
        market,
        "get_account",
        lambda: {"status": "ACTIVE", "cash": 50_000.0, "buying_power": 50_000.0, "portfolio_value": 50_000.0},
    )
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {
            "company_name": symbol,
            "market_cap": None,
            "sector": None,
            "next_earnings_date": None,
            "next_ex_dividend_date": None,
        },
    )
    html = report.render_report_html("TST", "covered_call", mode="pro", lang="en", static_export=True, asset_prefix=".")
    assert str(escape(CATALOG["en"]["rolling_body"])) in html


def test_rolling_explainer_absent_for_long_call(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["rolling_applicable"] is False

    html = report.render_report_html("TST", "long_call", mode="pro", lang="en", static_export=True, asset_prefix=".")
    assert str(escape(CATALOG["en"]["rolling_body"])) not in html


# --- payoff diagram + technical bias -----------------------------------------


def test_payoff_svg_is_a_nonempty_svg_document(patched_config, stub_market, stub_report_data):
    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["payoff_svg"].startswith("<svg")
    assert ctx["payoff_svg"].rstrip().endswith("</svg>")


@pytest.mark.parametrize("bias", ["bullish", "bearish", "mixed", "insufficient history"])
def test_bias_display_resolves_every_directional_bias(
    patched_config, stub_market, monkeypatch: pytest.MonkeyPatch, daily_bars, bias
):
    monkeypatch.setattr(market, "get_daily_bars", lambda ticker, **kwargs: daily_bars)
    monkeypatch.setattr(
        fundamentals,
        "get_fundamentals",
        lambda symbol: {"company_name": symbol, "market_cap": None, "sector": None, "next_earnings_date": None},
    )
    monkeypatch.setattr("optionslab.indicators.directional_bias", lambda closes: bias)

    ctx = report.build_report_context("TST", "long_call", static_export=True)
    assert ctx["bias_display"] != ""
    assert ctx["indicators"]["directional_bias"] == bias


# --- full render smoke test: catches broken Jinja before it ships -----------


@pytest.mark.parametrize("mode", ["learn", "pro"])
def test_render_report_html_smoke(patched_config, stub_market, stub_report_data, mode):
    html = report.render_report_html("TST", "long_call", mode=mode, lang="en", static_export=True, asset_prefix=".")
    assert html.startswith("<!doctype html>")
    assert "</html>" in html
    assert "TST" in html


# --- Learn-mode didactic explainers: sections + per-metric tooltips ---------

_EXPLAINED_METRICS = [
    "strike", "premium", "breakeven", "max_profit", "max_loss", "capital_required",
    "delta", "gamma", "theta", "vega", "rho", "implied_volatility",
    "pop_closed_form", "pop_monte_carlo", "probability_of_touch", "avg_win", "avg_loss", "score",
    "sma20", "sma50", "sma200", "rsi14", "hv30", "hv90", "range_52w", "directional_bias",
]

_EXPLAINED_SECTIONS = [
    "section_explain_contract",
    "section_explain_greeks",
    "section_explain_probability",
    "section_explain_technical",
]


def test_exactly_26_metrics_have_explainer_strings_in_both_catalogs():
    assert len(_EXPLAINED_METRICS) == 26
    for metric in _EXPLAINED_METRICS:
        key = f"explain_{metric}"
        assert key in CATALOG["en"], f"missing {key} in en catalog"
        assert key in CATALOG["pt-BR"], f"missing {key} in pt-BR catalog"


def test_learn_mode_renders_every_section_and_metric_explainer(patched_config, stub_market, stub_report_data):
    html = report.render_report_html("TST", "long_call", mode="learn", lang="en", static_export=True, asset_prefix=".")
    for key in _EXPLAINED_SECTIONS:
        assert str(escape(CATALOG["en"][key])) in html, f"missing section explainer {key}"
    for metric in _EXPLAINED_METRICS:
        key = f"explain_{metric}"
        assert str(escape(CATALOG["en"][key])) in html, f"missing metric explainer {key}"
    assert html.count('class="tip"') == len(_EXPLAINED_METRICS)


def test_pro_mode_renders_none_of_the_new_explainers(patched_config, stub_market, stub_report_data):
    html = report.render_report_html("TST", "long_call", mode="pro", lang="en", static_export=True, asset_prefix=".")
    assert 'class="tip"' not in html
    assert 'class="section-explain"' not in html
    for key in _EXPLAINED_SECTIONS:
        assert str(escape(CATALOG["en"][key])) not in html
    for metric in _EXPLAINED_METRICS:
        assert str(escape(CATALOG["en"][f"explain_{metric}"])) not in html


def test_learn_mode_explainers_render_in_pt_too(patched_config, stub_market, stub_report_data):
    html = report.render_report_html(
        "TST", "long_call", mode="learn", lang="pt-BR", static_export=True, asset_prefix="."
    )
    assert str(escape(CATALOG["pt-BR"]["section_explain_contract"])) in html
    assert str(escape(CATALOG["pt-BR"]["explain_delta"])) in html


def test_tooltip_text_forced_visible_in_print_css():
    """Regression guard for the PDF constraint: hover-only tooltips would be
    invisible in the Playwright print route, so @media print must force
    .tip-text to a static, always-visible block."""
    css = (PROJECT_ROOT / "static" / "css" / "report.css").read_text(encoding="utf-8")
    print_block = css[css.index("@media print {"):]
    tip_rule = print_block[print_block.index(".tip-text"):]
    assert "visibility: visible" in tip_rule.split("}")[0]
