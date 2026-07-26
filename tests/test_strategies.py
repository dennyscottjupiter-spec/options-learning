import numpy as np
import pytest

from optionslab.strategies import (
    build_cash_secured_put,
    build_covered_call,
    build_long_call,
    build_protective_put,
)


def test_long_call_payoff_matches_hand_math():
    contract = {"symbol": "TST", "strike": 100.0, "ask": 5.0, "bid": 4.8, "expiration": "2027-01-01"}
    strat = build_long_call(contract, underlying_price=95.0)

    assert strat.breakeven == [105.0]
    assert strat.capital_required == pytest.approx(500.0)
    assert strat.max_profit is None
    assert strat.max_loss == pytest.approx(-500.0)

    S_T = np.array([0.0, 100.0, 105.0, 150.0])
    payoff = strat.payoff_fn(S_T)
    assert payoff[0] == pytest.approx(-500.0)   # worthless: lose the whole premium
    assert payoff[1] == pytest.approx(-500.0)   # at strike: still lose the premium
    assert payoff[2] == pytest.approx(0.0)      # at breakeven: flat
    assert payoff[3] == pytest.approx(4500.0)   # (150-100)*100 - 500


def test_cash_secured_put_payoff_matches_hand_math():
    contract = {"symbol": "TST", "strike": 90.0, "ask": 3.2, "bid": 3.0, "expiration": "2027-01-01"}
    strat = build_cash_secured_put(contract, underlying_price=95.0)

    assert strat.breakeven == [87.0]
    assert strat.capital_required == pytest.approx(9000.0)
    assert strat.max_profit == pytest.approx(300.0)
    assert strat.max_loss == pytest.approx(300.0 - 9000.0)

    S_T = np.array([0.0, 87.0, 90.0, 200.0])
    payoff = strat.payoff_fn(S_T)
    assert payoff[0] == pytest.approx(300.0 - 9000.0)  # stock craters to 0
    assert payoff[1] == pytest.approx(0.0)             # breakeven
    assert payoff[2] == pytest.approx(300.0)           # at strike: max profit reached
    assert payoff[3] == pytest.approx(300.0)           # deep OTM put: still max profit


def test_covered_call_payoff_matches_hand_math():
    contract = {"symbol": "TST", "strike": 110.0, "ask": 2.7, "bid": 2.5, "expiration": "2027-01-01"}
    S0 = 100.0
    strat = build_covered_call(contract, underlying_price=S0)

    assert strat.breakeven == [pytest.approx(97.5)]
    assert strat.capital_required == pytest.approx(10000.0)
    assert strat.max_profit == pytest.approx((110 - 100) * 100 + 250.0)
    assert strat.max_loss == pytest.approx(-100 * 100 + 250.0)

    S_T = np.array([0.0, 97.5, 110.0, 200.0])
    payoff = strat.payoff_fn(S_T)
    assert payoff[0] == pytest.approx(-100 * 100 + 250.0)  # stock craters, keep premium
    assert payoff[1] == pytest.approx(0.0)                  # breakeven
    assert payoff[2] == pytest.approx(1250.0)                # called away at strike
    assert payoff[3] == pytest.approx(1250.0)                # capped even if stock rips


def test_protective_put_payoff_matches_hand_math():
    contract = {"symbol": "TST", "strike": 90.0, "ask": 3.5, "bid": 3.3, "expiration": "2027-01-01"}
    S0 = 100.0
    strat = build_protective_put(contract, underlying_price=S0)

    assert strat.breakeven == [pytest.approx(103.5)]
    assert strat.capital_required == pytest.approx(350.0)
    assert strat.max_profit is None
    assert strat.max_loss == pytest.approx((90 - 100) * 100 - 350.0)

    S_T = np.array([0.0, 90.0, 103.5, 200.0])
    payoff = strat.payoff_fn(S_T)
    assert payoff[0] == pytest.approx((90 - 100) * 100 - 350.0)  # floored at strike
    assert payoff[1] == pytest.approx((90 - 100) * 100 - 350.0)  # still floored
    assert payoff[2] == pytest.approx(0.0)                        # breakeven
    assert payoff[3] == pytest.approx((200 - 100) * 100 - 350.0)  # uncapped upside
