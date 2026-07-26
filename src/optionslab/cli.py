"""
Entry points installed by `pip install -e .` (see [project.scripts] in
pyproject.toml). scripts/run_web.py and scripts/check_account.py remain as
thin shims so the documented `python scripts\\run_web.py` invocation keeps
working unchanged.
"""
from __future__ import annotations

import sys

import uvicorn
from alpaca.trading.client import TradingClient

from optionslab.creds import CredentialsNotSetError, get_alpaca_credentials


def web() -> None:
    uvicorn.run("optionslab.web:app", host="127.0.0.1", port=8420, reload=False)


def check_account() -> None:
    try:
        api_key, api_secret = get_alpaca_credentials()
    except CredentialsNotSetError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    client = TradingClient(api_key, api_secret, paper=True)
    account = client.get_account()

    print("Alpaca paper account (read-only check):")
    print(f"  status:         {account.status}")
    print(f"  cash:           ${float(account.cash):,.2f}")
    print(f"  buying_power:   ${float(account.buying_power):,.2f}")
    print(f"  portfolio_value:${float(account.portfolio_value):,.2f}")
