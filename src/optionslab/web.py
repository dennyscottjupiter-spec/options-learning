"""FastAPI app: dashboard (watchlist + ticker analyzer), the report page, and
its PDF export."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from optionslab import fundamentals, market, report, watchlist
from optionslab.select import StrategyType

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

app = FastAPI(title="options-learning")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _watchlist_snapshot(ticker: str) -> dict:
    """One dashboard card's data. Never lets a single bad/delisted ticker in
    the watchlist take down the whole home page."""
    try:
        bars = market.get_daily_bars(ticker, lookback_days=5)
        closes = [b["close"] for b in bars]
        price = closes[-1]
        prev = closes[-2] if len(closes) > 1 else price
        change_pct = (price - prev) / prev * 100 if prev else 0.0
        fund = fundamentals.get_fundamentals(ticker)
        return {
            "ticker": ticker,
            "ok": True,
            "company_name": fund.get("company_name", ticker),
            "price": price,
            "change_pct": change_pct,
        }
    except Exception:
        return {"ticker": ticker, "ok": False}


@app.get("/", response_class=HTMLResponse)
def home(lang: str = Query("en")):
    tickers = watchlist.get_watchlist()
    cards = [_watchlist_snapshot(t) for t in tickers]
    other_lang = "pt-BR" if lang == "en" else "en"
    html = report.render_home_html(lang, cards, lang_toggle_href=f"/?lang={other_lang}")
    return HTMLResponse(html)


@app.get("/analyze")
def analyze(
    ticker: str = Query(...),
    strategy: StrategyType = Query("long_call"),
    mode: str = Query("learn"),
    lang: str = Query("en"),
    expiration: str | None = Query(None),
):
    ticker = ticker.strip().upper()
    q = f"strategy={strategy}&mode={mode}&lang={lang}"
    if expiration:
        q += f"&expiration={expiration}"
    return RedirectResponse(f"/report/{ticker}?{q}", status_code=303)


@app.post("/watchlist/add")
def watchlist_add(ticker: str = Form(...), lang: str = Form("en")):
    watchlist.add_ticker(ticker)
    return RedirectResponse(f"/?lang={lang}", status_code=303)


@app.post("/watchlist/remove")
def watchlist_remove(ticker: str = Form(...), lang: str = Form("en")):
    watchlist.remove_ticker(ticker)
    return RedirectResponse(f"/?lang={lang}", status_code=303)


def _build_nav(ticker: str, strategy: str, mode: str, lang: str, expiration: str | None) -> dict:
    def url(mode_val: str, lang_val: str) -> str:
        q = f"strategy={strategy}&mode={mode_val}&lang={lang_val}"
        if expiration:
            q += f"&expiration={expiration}"
        return f"/report/{ticker}?{q}"

    other_lang = "pt-BR" if lang == "en" else "en"
    return {
        "mode_learn_href": url("learn", lang),
        "mode_pro_href": url("pro", lang),
        "lang_toggle_href": url(mode, other_lang),
    }


@app.get("/report/{ticker}", response_class=HTMLResponse)
def get_report(
    ticker: str,
    strategy: StrategyType = Query("long_call"),
    mode: str = Query("learn"),
    lang: str = Query("en"),
    expiration: str | None = Query(None),
):
    nav = _build_nav(ticker, strategy, mode, lang, expiration)
    in_watchlist = ticker.strip().upper() in watchlist.get_watchlist()
    html = report.render_report_html(ticker, strategy, expiration, mode, lang, nav, in_watchlist)
    return HTMLResponse(html)


@app.get("/report/{ticker}/pdf")
def get_report_pdf(
    request: Request,
    ticker: str,
    strategy: StrategyType = Query("long_call"),
    mode: str = Query("learn"),
    lang: str = Query("en"),
    expiration: str | None = Query(None),
):
    base_url = str(request.base_url).rstrip("/")
    pdf_path = report.generate_pdf(ticker, strategy, base_url, expiration, mode, lang)
    return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)
