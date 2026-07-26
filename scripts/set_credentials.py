"""
Run this yourself, once, whenever you need to set or rotate your Alpaca paper keys:

    python3 scripts\\set_credentials.py

Keys are typed via getpass (never echoed, never logged) and written straight to
Windows Credential Manager (DPAPI-encrypted against your Windows login). Nothing
is written to any file, and this script never prints the values back.
"""
import getpass
import sys

import keyring

SERVICE = "options-learning-alpaca"


def main() -> None:
    print("Setting Alpaca PAPER trading credentials in Windows Credential Manager.")
    print("Input is hidden as you type.\n")

    api_key = getpass.getpass("Alpaca API Key ID: ").strip()
    api_secret = getpass.getpass("Alpaca API Secret Key: ").strip()

    if not api_key or not api_secret:
        print("Both values are required. Nothing was saved.", file=sys.stderr)
        sys.exit(1)

    keyring.set_password(SERVICE, "api_key", api_key)
    keyring.set_password(SERVICE, "api_secret", api_secret)

    print("\nSaved. Credentials are stored in Windows Credential Manager under")
    print(f'  Windows Credentials -> Generic Credentials -> "{SERVICE}"')
    print("They were never written to a file and never printed above.")


if __name__ == "__main__":
    main()
