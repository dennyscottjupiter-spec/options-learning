"""FastAPI app: serves the report page and its PDF export."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from optionslab import report
from optionslab.select import StrategyType

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"

app = FastAPI(title="options-learning")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
    html = report.render_report_html(ticker, strategy, expiration, mode, lang, nav)
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
