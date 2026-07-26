"""
Spawns alpaca-mcp-server with credentials injected into its environment at
process start — never written to a .env file or any config on disk.

Usage: point your MCP client (e.g. Claude Code's .mcp.json) at this script
instead of `uvx alpaca-mcp-server` directly:

    { "command": "python3", "args": ["scripts/run_mcp.py"] }

Requires `uvx` (ships with `uv`) on PATH, and credentials already set via
scripts/set_credentials.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from optionslab.creds import CredentialsNotSetError, get_alpaca_credentials  # noqa: E402


def main() -> None:
    try:
        api_key, api_secret = get_alpaca_credentials()
    except CredentialsNotSetError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["ALPACA_API_KEY"] = api_key
    env["ALPACA_SECRET_KEY"] = api_secret
    env["ALPACA_PAPER_TRADE"] = "true"

    subprocess.run(["uvx", "alpaca-mcp-server"], env=env, check=True)


if __name__ == "__main__":
    main()
