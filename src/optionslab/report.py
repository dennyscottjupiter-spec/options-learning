"""
Renders the report template (used verbatim by both the web view and the PDF
export — same HTML, same CSS, guaranteed identical) and drives Playwright to
print a running report page to PDF, auto-archived under archive/.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from optionslab import fundamentals, indicators, market, select
from optionslab.config import load_config
from optionslab.i18n import get_strategy_blurb, get_strategy_name, get_strings
from optionslab.svg import render_payoff_svg

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
ARCHIVE_DIR = Path(__file__).resolve().parents[2] / "archive"

_BIAS_KEY = {
    "bullish": "bias_bullish",
    "bearish": "bias_bearish",
    "mixed": "bias_mixed",
    "insufficient history": "bias_insufficient",
}


def _money(value: float) -> str:
    """Formats a signed dollar amount as '$1,234.56' or '-$1,234.56' — never
    '$-1234.56', which is what Python's default sign placement produces."""
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "jinja"]),
    )
    env.filters["money"] = _money
    return env


def _format_market_cap(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.1f}B"
    if value >= 1e6:
        return f"${value / 1e6:.1f}M"
    return f"${value:,.0f}"


def build_report_context(
    ticker: str,
    strategy_type: select.StrategyType,
    expiration_date: str | None = None,
    mode: str = "learn",
    lang: str = "en",
    nav: dict | None = None,
) -> dict:
    ticker = ticker.upper()
    cfg = load_config()
    r = cfg["math"]["risk_free_rate"]

    result = select.select_best(ticker, strategy_type, expiration_date)
    best = result["best"]
    strategy = best["strategy"]
    contract = best["contract"]

    bars = market.get_daily_bars(ticker, lookback_days=400)
    ind = indicators.compute_all(bars)

    fund = fundamentals.get_fundamentals(ticker)

    exp_date = datetime.strptime(strategy.expiration, "%Y-%m-%d").date()
    T = max((exp_date - date.today()).days, 1) / 365.0
    sigma = contract.get("implied_volatility") or 0.0
    payoff_svg = render_payoff_svg(strategy, result["spot_price"], T, r, sigma)

    earnings_warning = False
    if fund.get("next_earnings_date"):
        next_earnings = datetime.strptime(fund["next_earnings_date"], "%Y-%m-%d").date()
        if date.today() <= next_earnings <= exp_date:
            earnings_warning = True

    s = get_strings(lang)
    strings_dict = {**s}

    why_best = None
    if result["why_best_data"]:
        why_best = s["why_best_template"].format(**result["why_best_data"])

    return {
        "lang": lang,
        "mode": mode,
        "s": strings_dict,
        "nav": nav or {"mode_learn_href": "#", "mode_pro_href": "#", "lang_toggle_href": "#"},
        "ticker": ticker,
        "company_name": fund.get("company_name", ticker),
        "sector": fund.get("sector"),
        "market_cap_display": _format_market_cap(fund.get("market_cap")),
        "next_earnings_date": fund.get("next_earnings_date"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "spot_price": result["spot_price"],
        "strategy_type": strategy_type,
        "strategy_name": get_strategy_name(strategy_type, lang),
        "strategy_blurb": get_strategy_blurb(strategy_type, lang),
        "strategy": strategy,
        "contract": contract,
        "best": best,
        "runner_up": result["runner_up"],
        "why_best": why_best,
        "candidates_evaluated": result["candidates_evaluated"],
        "payoff_svg": payoff_svg,
        "earnings_warning": earnings_warning,
        "indicators": ind,
        "bias_display": s[_BIAS_KEY.get(ind["directional_bias"], "bias_insufficient")],
    }


def render_report_html(
    ticker: str,
    strategy_type: select.StrategyType,
    expiration_date: str | None = None,
    mode: str = "learn",
    lang: str = "en",
    nav: dict | None = None,
) -> str:
    context = build_report_context(ticker, strategy_type, expiration_date, mode, lang, nav)
    template = _env().get_template("report.html.jinja")
    return template.render(**context)


def generate_pdf(
    ticker: str,
    strategy_type: select.StrategyType,
    base_url: str,
    expiration_date: str | None = None,
    mode: str = "learn",
    lang: str = "en",
) -> Path:
    """Navigates Playwright to the live report page (same HTML/CSS the browser
    shows) and prints it to PDF, archived as archive/YYYY-MM-DD_TICKER_STRATEGY.pdf."""
    from playwright.sync_api import sync_playwright

    ticker = ticker.upper()
    ARCHIVE_DIR.mkdir(exist_ok=True)
    filename = f"{date.today().isoformat()}_{ticker}_{strategy_type}.pdf"
    out_path = ARCHIVE_DIR / filename

    url = f"{base_url}/report/{ticker}?strategy={strategy_type}&mode={mode}&lang={lang}"
    if expiration_date:
        url += f"&expiration={expiration_date}"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.pdf(path=str(out_path), format="A4", print_background=True, margin={"top": "0", "bottom": "0"})
        browser.close()

    return out_path
