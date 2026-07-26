"""
Read-only sanity check for Phase 0: confirms credentials work by printing paper
account status and buying power. Never prints the API key or secret.

    python3 scripts\\check_account.py
"""
from __future__ import annotations

import sys

from alpaca.trading.client import TradingClient

from optionslab.creds import CredentialsNotSetError, get_alpaca_credentials


def main() -> None:
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


if __name__ == "__main__":
    main()
