"""
Renders the report template (used verbatim by both the web view and the PDF
export — same HTML, same CSS, guaranteed identical) and drives Playwright to
print a running report page to PDF, auto-archived under archive/.
"""
from __future__ import annotations

import ast
import re
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from optionslab import fundamentals, indicators, market, select
from optionslab.config import load_config
from optionslab.i18n import get_strategy_blurb, get_strategy_name, get_strings
from optionslab.svg import render_payoff_svg

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = PROJECT_ROOT / "templates"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
_SRC_DIR = PROJECT_ROOT / "src" / "optionslab"

GITHUB_REPO = "dennyscottjupiter-spec/options-learning"
GITHUB_BRANCH = "main"

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


_FORMULA_TOKEN_RE = re.compile(
    r"(?P<func>\b(?:N|ln|mean)\b)"
    r"|(?P<ident>\b(?:POP_MC|capital_required|avg_win|avg_loss|breakeven|payoff|GBM|seed|S_T|DTE|d2|S|r|T)\b|σ)"
    r"|(?P<num>\b\d{1,3}(?:,\d{3})+\b|\b\d+\b)"
    r"|(?P<op>[()\[\]{}=+/,.<>]|−|—|×|÷|≤|≥|²|√)"
)


def _highlight_formula(formula: str) -> Markup:
    """Tokenizes one of the six known methodology formula strings into colour-
    coded spans (function / identifier / number / operator), server-side so it
    works identically in the live app, the Playwright-rendered PDF, and the
    static export with no client-side JS or highlighting library."""
    out: list[str] = []
    pos = 0
    for m in _FORMULA_TOKEN_RE.finditer(formula):
        if m.start() > pos:
            out.append(str(escape(formula[pos : m.start()])))
        kind = m.lastgroup
        out.append(f'<span class="tok-{kind}">{escape(m.group())}</span>')
        pos = m.end()
    out.append(str(escape(formula[pos:])))
    return Markup("".join(out))


def _function_line(file_path: Path, func_name: str) -> int | None:
    """Best-effort line number of `def func_name` in `file_path`, for anchoring
    a Source-column link. Returns None (unanchored link) rather than raising
    if the file can't be parsed — the link to the file itself still works."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node.lineno
    return None


def _linkify_source(source: str, static_export: bool) -> Markup:
    """Turns each `file.py::func[, func2]` segment of a methodology `source`
    string into one link per function — a GitHub blob permalink for the
    static export (never the local machine's path) or the read-only
    /source/{module} route for the live app, anchored to the function's line
    where it can be located. Segments chained with ' → ' each get their own
    link(s); the arrow itself is left as plain text."""
    rendered_parts = []
    for part in source.split(" → "):
        file_path_str, sep, funcs_str = part.partition("::")
        if not sep:
            rendered_parts.append(str(escape(part)))
            continue
        file_name = file_path_str.rsplit("/", 1)[-1]
        real_path = _SRC_DIR / file_name
        links = []
        for func in (f.strip() for f in funcs_str.split(",")):
            line = _function_line(real_path, func)
            anchor = f"#L{line}" if line else ""
            if static_export:
                href = f"https://github.com/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/src/optionslab/{file_name}{anchor}"
            else:
                href = f"/source/{file_name}{anchor}"
            links.append(f'<a href="{escape(href)}">{escape(file_name)}::{escape(func)}</a>')
        rendered_parts.append(", ".join(links))
    return Markup(" → ".join(rendered_parts))


def render_source_html(module: str) -> str | None:
    """Read-only view of one src/optionslab module, for the methodology
    table's Source links in the live app. Returns None for anything outside
    src/optionslab/ (no path separators, no traversal) so the caller 404s."""
    if "/" in module or "\\" in module or not module.endswith(".py"):
        return None
    resolved = (_SRC_DIR / module).resolve()
    try:
        resolved.relative_to(_SRC_DIR.resolve())
    except ValueError:
        return None
    if not resolved.is_file():
        return None
    lines = resolved.read_text(encoding="utf-8").splitlines()
    body = "\n".join(
        f'<span id="L{i}" class="src-line">{escape(line)}</span>' for i, line in enumerate(lines, start=1)
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(module)} — Options Lab source</title>"
        "<link rel='stylesheet' href='/static/css/report.css'>"
        "<style>.src-pre{background:var(--panel);border:1px solid var(--hairline);"
        "border-radius:8px;padding:16px;overflow-x:auto;font-family:var(--font-mono);"
        "font-size:12.5px;line-height:1.6;color:var(--ink);}"
        ".src-line{display:block;white-space:pre;}"
        ".src-line:target{background:var(--indigo-soft);}</style></head>"
        f"<body><div class='page'><h1>{escape(module)}</h1>"
        f"<pre class='src-pre'>{body}</pre></div></body></html>"
    )


def _methodology_rows(mc_paths: int, mc_seed: int, src_dir: str, static_export: bool) -> list[dict]:
    """Every 'Probability of profit' figure traces to one of these — exact
    formula as coded, plus the path to the function that computes it, so the
    number is checkable, not asserted. `src_dir` is the absolute local path
    for the live app, or a relative repo path for the public static export —
    never leak the local machine's directory structure into a published page."""
    pop_py = f"{src_dir}/pop.py"
    bs_py = f"{src_dir}/bs.py"
    select_py = f"{src_dir}/select.py"
    rows = [
        {
            "metric_key": "pop_closed_form",
            "formula": "N(d2) [breakeven above spot] or N(−d2) [below] — "
            "d2 = [ln(S/breakeven) + (r − σ²/2)T] / (σ√T)",
            "source": f"{bs_py}::d1_d2 → {pop_py}::probability_of_profit_closed_form",
        },
        {
            "metric_key": "pop_monte_carlo",
            "formula": f"mean(1{{S_T beats breakeven}}) over {mc_paths:,} simulated GBM "
            f"paths (antithetic variates, seed={mc_seed})",
            "source": f"{pop_py}::simulate_paths, probability_of_profit_monte_carlo",
        },
        {
            "metric_key": "probability_of_touch",
            "formula": "mean(1{path touches breakeven at any point before expiry}), "
            "same simulated paths",
            "source": f"{pop_py}::probability_of_touch",
        },
        {
            "metric_key": "avg_win",
            "formula": "mean(payoff) over simulated paths where payoff > 0",
            "source": f"{select_py}::evaluate_contract",
        },
        {
            "metric_key": "avg_loss",
            "formula": "mean(−payoff) over simulated paths where payoff ≤ 0",
            "source": f"{select_py}::evaluate_contract",
        },
        {
            "metric_key": "score",
            "formula": "(POP_MC × avg_win − (1 − POP_MC) × avg_loss) "
            "÷ capital_required × (365 ÷ DTE)",
            "source": f"{select_py}::evaluate_contract",
        },
    ]
    for row in rows:
        row["formula_html"] = _highlight_formula(row["formula"])
        row["source_html"] = _linkify_source(row["source"], static_export)
    return rows


def build_report_context(
    ticker: str,
    strategy_type: select.StrategyType,
    expiration_date: str | None = None,
    mode: str = "learn",
    lang: str = "en",
    nav: dict | None = None,
    in_watchlist: bool = False,
    static_export: bool = False,
    asset_prefix: str = "/static",
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

    strategy_options = [(t, get_strategy_name(t, lang)) for t in select.STRATEGY_TYPES]
    src_dir_display = "src/optionslab" if static_export else str(_SRC_DIR).replace("\\", "/")
    methodology = _methodology_rows(
        cfg["math"]["monte_carlo_paths"], cfg["math"]["monte_carlo_seed"], src_dir_display, static_export
    )

    return {
        "lang": lang,
        "mode": mode,
        "s": strings_dict,
        "nav": nav or {"mode_learn_href": "#", "mode_pro_href": "#", "lang_toggle_href": "#"},
        "in_watchlist": in_watchlist,
        "strategy_options": strategy_options,
        "methodology": methodology,
        "src_dir": src_dir_display,
        "static_export": static_export,
        "asset_prefix": asset_prefix,
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
    in_watchlist: bool = False,
    static_export: bool = False,
    asset_prefix: str = "/static",
) -> str:
    context = build_report_context(
        ticker, strategy_type, expiration_date, mode, lang, nav, in_watchlist, static_export, asset_prefix
    )
    template = _env().get_template("report.html.jinja")
    return template.render(**context)


def render_home_html(lang: str, cards: list[dict], lang_toggle_href: str) -> str:
    s = get_strings(lang)
    context = {
        "lang": lang,
        "s": s,
        "cards": cards,
        "lang_toggle_href": lang_toggle_href,
        "strategy_options": [(t, get_strategy_name(t, lang)) for t in select.STRATEGY_TYPES],
    }
    template = _env().get_template("home.html.jinja")
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
