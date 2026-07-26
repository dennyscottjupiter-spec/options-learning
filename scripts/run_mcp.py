"""
Launches the official Alpaca MCP server (github.com/alpacahq/alpaca-mcp-server,
installed via requirements.txt) with credentials injected from Windows
Credential Manager at process start — no plaintext .env file or MCP-config
secret ever touches disk.

Read-only by design: ALPACA_TOOLSETS excludes "trading" (the order-placement
and position-closing tools), and ALPACA_PAPER_TRADE is hardcoded to "true" —
this project never places an order and never touches a live account, on
paper or otherwise.

Registered with Claude Code via:

    claude mcp add options-learning-alpaca -- <venv-python> scripts/run_mcp.py
"""
from __future__ import annotations

import os
import sys

from optionslab.creds import CredentialsNotSetError, get_alpaca_credentials

READ_ONLY_TOOLSETS = "account,watchlists,assets,stock-data,crypto-data,options-data,corporate-actions"


def main() -> None:
    try:
        api_key, api_secret = get_alpaca_credentials()
    except CredentialsNotSetError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    os.environ["ALPACA_API_KEY"] = api_key
    os.environ["ALPACA_SECRET_KEY"] = api_secret
    os.environ["ALPACA_PAPER_TRADE"] = "true"
    os.environ["ALPACA_TOOLSETS"] = READ_ONLY_TOOLSETS

    from alpaca_mcp_server.cli import main as alpaca_main

    sys.argv = [sys.argv[0]]  # this wrapper takes no args of its own
    alpaca_main()


if __name__ == "__main__":
    main()
