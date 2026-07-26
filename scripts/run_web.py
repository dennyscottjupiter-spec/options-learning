"""Runs the local web app: python3 scripts\\run_web.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("optionslab.web:app", host="127.0.0.1", port=8420, reload=False)
