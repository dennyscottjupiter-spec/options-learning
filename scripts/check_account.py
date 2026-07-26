"""
Read-only sanity check for Phase 0: confirms credentials work by printing paper
account status and buying power. Never prints the API key or secret.

    python3 scripts\\check_account.py
"""
from optionslab.cli import check_account

if __name__ == "__main__":
    check_account()
