"""Loads config.toml (non-secret settings) once per process."""
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.toml"


@lru_cache(maxsize=1)
def load_config() -> dict:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)
