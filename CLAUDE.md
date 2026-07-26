# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A **learning** tool for US stock options: given a ticker and one of four strategies, it fetches a live option chain from Alpaca's **paper** API, evaluates candidate contracts, picks the best one, and renders a bilingual (EN / pt-BR) report that explains *why* — every number traceable to the function that computed it.

Hard constraints baked into the design:
- **Read-only, paper-only.** Nothing in this repo places an order. `market.py` uses `TradingClient(..., paper=True)`; `scripts/run_mcp.py` strips the `trading` toolset from the Alpaca MCP server.
- **No secrets on disk.** Alpaca keys live in Windows Credential Manager, read exclusively through `optionslab/creds.py` — never `os.environ`, never a config file, never `.env`.
- **Transparency is the product.** The report ships a methodology table mapping each metric to its exact formula *and* source path. If you change a formula, update `report.py::_methodology_rows` in the same edit.

## Commands

All commands run from the repo root using the venv interpreter (`.venv\Scripts\python.exe`, Python 3.14).

```powershell
.venv\Scripts\python.exe -m pytest -q                          # full suite (69 tests, ~28s)
.venv\Scripts\python.exe -m pytest tests\test_pop.py -q        # one file
.venv\Scripts\python.exe -m pytest -q -k monte_carlo           # one test by name

.venv\Scripts\python.exe scripts\run_web.py                    # web app -> http://127.0.0.1:8420
.venv\Scripts\python.exe scripts\check_account.py              # verify credentials work (read-only)
.venv\Scripts\python.exe scripts\set_credentials.py            # set/rotate Alpaca paper keys (getpass)
.venv\Scripts\python.exe scripts\export_static_demo.py         # regenerate docs/ for GitHub Pages
```

`pip install -e .` also installs `options-web` / `options-check` entry points (`.venv\Scripts\options-web.exe`), wired through `src/optionslab/cli.py`. `scripts/run_web.py` and `scripts/check_account.py` are thin shims onto that same module, kept so the commands above keep working unchanged. Tests are pure math (`bs`, `pop`, `indicators`, `strategies`) and hit no network; the data layer has no test coverage.

## Architecture

Layered, one direction only: **config/creds → market data → math → strategies → selection → report → web**.

- **`config.py` / `creds.py`** — the only two entry points for settings and secrets. `load_config()` is `lru_cache`d; every tunable (risk-free rate, MC paths/seed, DTE windows, liquidity gates, watchlist seed) lives in `config.toml`, not in code.
- **`market.py`** — Alpaca REST (bars, option-chain snapshots, account, positions). Every read passes through `cache.py` (disk, TTL per call: 15 min bars, 2 min chains, 24 h fundamentals) and a `RateLimitTracker` that *raises* before the free plan's 200 req/min cap is hit. Alpaca's snapshot has **no open-interest field**, so liquidity is judged by quoted size + spread. `fundamentals.py` fills the gaps Alpaca lacks (market cap, sector, earnings date) via yfinance.
- **`bs.py` / `pop.py`** — the math engine. `bs.py` is the *fallback* used whenever Alpaca returns no Greeks/IV (zero quotes, 0DTE); its Greek conventions deliberately match Alpaca's (theta per calendar day, vega/rho per 1 percentage point) so the two sources are interchangeable. `pop.py` runs two independent POP engines — closed-form `N(d2)` and Monte Carlo GBM paths (antithetic variates, fixed seed) — and their disagreement beyond `pop_disagreement_flag_pp` is surfaced in the report rather than silently resolved. POP is always computed at the strategy's **breakeven**, never its strike.
- **`strategies.py`** — the four strategies reduced to one shape: `StrategyResult` with a `payoff_fn(S_T) -> net $ P&L`. For covered call and protective put the payoff includes the 100 shares already held, not just the option leg. All four are bullish-shaped, hence `pop_direction="above"` on all of them — stored explicitly, not assumed.
- **`select.py`** — the orchestrator. Picks the expiration window, enriches contracts with local Greeks where missing (tagging `greeks_source`), narrows to the 12 strikes nearest the strategy's target delta, then **two-phase evaluation**: a cheap 5 000-path screening pass ranks the band, only the top 2 get the full 100 000-path run. It returns raw comparison numbers (`why_best_data`), never formatted prose — it has no i18n knowledge.
- **`i18n.py` / `report.py` / `svg.py` / `templates/`** — `i18n.py` holds two string catalogs; `report.py` picks one by `lang` and hands the whole dict to Jinja as `s`, so **templates branch on `mode` (learn/pro) but never on language**. `svg.py` hand-builds the payoff diagram as inline SVG (not matplotlib) so browser and PDF render pixel-identically, with the lognormal terminal distribution drawn as a ribbon behind the payoff line.
- **`web.py`** — thin FastAPI layer: dashboard, `/report/{ticker}`, `/report/{ticker}/pdf`. The PDF path drives Playwright to the *live report URL*, so PDF and web page are the same HTML/CSS by construction — never build a separate print template.

### Two output targets, one template

`report.render_report_html()` serves both the live app and the static GitHub Pages export (`docs/`). The `static_export` / `asset_prefix` flags are what differ. Note `static_export=True` also swaps the methodology table's absolute local `src/` path for a repo-relative one — **never leak the local machine's directory structure into a published page**.

## Conventions

- Module docstrings carry the *why* (design rationale, data-source quirks, math caveats). They are load-bearing documentation — keep them current when behavior changes.
- Monte Carlo uses a fixed seed from config, so runs are reproducible; don't introduce unseeded randomness.
- Liquidity failures are **flagged, never filtered out** — the caller still receives the contract with `liquidity_ok: False`.
- `archive/`, `cache/`, and `watchlist.json` are per-machine state and gitignored.
- The SVG palette in `svg.py` must stay in sync with `static/css/report.css`.
