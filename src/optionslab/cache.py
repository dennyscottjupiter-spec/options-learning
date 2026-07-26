"""Tiny disk cache shared by market.py and fundamentals.py, keyed by a string
signature with a per-call TTL. Values must be JSON-serializable."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode()).hexdigest()[:32]
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{digest}.json"


def cache_get(key: str, ttl_seconds: int) -> Any | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl_seconds:
        return None
    return json.loads(path.read_text())


def cache_set(key: str, value: Any) -> None:
    _cache_path(key).write_text(json.dumps(value))
