"""
Builds a static, backend-free snapshot of the report page into docs/ for
GitHub Pages. Frozen real sample data (one live fetch against Alpaca's paper
API), not a live app: no watchlist, no ticker analyzer, no PDF export, no
credentials anywhere in the output. Run: python3 scripts\\export_static_demo.py
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from optionslab import report  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TICKER = "AAPL"
STRATEGY = "long_call"

_VARIANTS = [
    ("en", "learn", "report-aapl-en-learn.html"),
    ("en", "pro", "report-aapl-en-pro.html"),
    ("pt-BR", "learn", "report-aapl-pt-learn.html"),
    ("pt-BR", "pro", "report-aapl-pt-pro.html"),
]


def _filename(lang: str, mode: str) -> str:
    for l, m, fname in _VARIANTS:
        if l == lang and m == mode:
            return fname
    raise ValueError(lang, mode)


def main() -> None:
    for sub in ("css", "js", "img"):
        (DOCS / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "static" / "css" / "report.css", DOCS / "css" / "report.css")
    shutil.copy(ROOT / "static" / "js" / "theme.js", DOCS / "js" / "theme.js")
    shutil.copy(ROOT / "static" / "img" / "about.jpg", DOCS / "img" / "about.jpg")

    for lang, mode, fname in _VARIANTS:
        nav = {
            "mode_learn_href": _filename(lang, "learn"),
            "mode_pro_href": _filename(lang, "pro"),
            "lang_toggle_href": _filename("pt-BR" if lang == "en" else "en", mode),
        }
        html = report.render_report_html(
            TICKER, STRATEGY, mode=mode, lang=lang, nav=nav,
            static_export=True, asset_prefix=".",
        )
        (DOCS / fname).write_text(html, encoding="utf-8")
        print(f"wrote {fname}")

    s = report.get_strings("en")
    index_context = {
        "lang": "en",
        "s": s,
    }
    index_html = report._env().get_template("static_index.html.jinja").render(**index_context)
    (DOCS / "index.html").write_text(index_html, encoding="utf-8")
    print("wrote index.html")


if __name__ == "__main__":
    main()
