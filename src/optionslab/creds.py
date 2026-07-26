"""
Single choke point for reading Alpaca credentials. Every other module gets keys
through this file — never through os.environ, never through a config file.

Keys live in Windows Credential Manager (see scripts/set_credentials.py) and are
read via `keyring`, which decrypts them with DPAPI against the current Windows
login. They exist in this process's memory only for as long as they're needed.
"""
from __future__ import annotations

import keyring

SERVICE = "options-learning-alpaca"


class CredentialsNotSetError(RuntimeError):
    pass


def get_alpaca_credentials() -> tuple[str, str]:
    """Return (api_key, api_secret). Raises if not yet configured."""
    api_key = keyring.get_password(SERVICE, "api_key")
    api_secret = keyring.get_password(SERVICE, "api_secret")

    if not api_key or not api_secret:
        raise CredentialsNotSetError(
            "Alpaca credentials are not set. Run: python3 scripts/set_credentials.py"
        )

    return api_key, api_secret
