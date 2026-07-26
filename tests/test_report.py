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

import pytest

from optionslab import fundamentals, market, report
from optionslab.i18n import CATALOG

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
