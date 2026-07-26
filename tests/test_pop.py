import pytest

from optionslab.pop import (
    probability_of_profit_closed_form,
    probability_of_profit_monte_carlo,
    probability_of_touch,
    simulate_paths,
)


@pytest.mark.parametrize(
    "S,breakeven,T,r,sigma,direction",
    [
        (100, 110, 1.0, 0.05, 0.25, "above"),   # long call shaped
        (100, 90, 1.0, 0.05, 0.25, "below"),    # long put shaped
        (355.74, 360, 45 / 365, 0.043, 0.30, "above"),
        (355.74, 340, 45 / 365, 0.043, 0.30, "below"),
        (50, 55, 180 / 365, 0.043, 0.5, "above"),  # LEAPS-ish, higher vol
    ],
)
def test_monte_carlo_agrees_with_closed_form_within_1pp(S, breakeven, T, r, sigma, direction):
    closed_form = probability_of_profit_closed_form(S, breakeven, T, r, sigma, direction)
    paths = simulate_paths(S, T, r, sigma, n_paths=100_000, seed=7)
    mc = probability_of_profit_monte_carlo(paths[:, -1], breakeven, direction)
    assert abs(closed_form - mc) < 0.01, f"closed_form={closed_form:.4f} mc={mc:.4f}"


def test_reproducible_with_fixed_seed():
    paths_a = simulate_paths(S=100, T=1.0, r=0.05, sigma=0.25, n_paths=10_000, seed=7)
    paths_b = simulate_paths(S=100, T=1.0, r=0.05, sigma=0.25, n_paths=10_000, seed=7)
    assert (paths_a == paths_b).all()


def test_probability_of_touch_is_at_least_terminal_pop():
    # Touching a barrier before expiry is at least as likely as ending beyond it.
    S, T, r, sigma = 100, 1.0, 0.05, 0.30
    barrier = 120
    paths = simulate_paths(S, T, r, sigma, n_paths=50_000, seed=7)
    touch_prob = probability_of_touch(paths, barrier, "up")
    terminal_prob = probability_of_profit_monte_carlo(paths[:, -1], barrier, "above")
    assert touch_prob >= terminal_prob


def test_probability_of_touch_own_starting_price_is_certain():
    S, T, r, sigma = 100, 1.0, 0.05, 0.30
    paths = simulate_paths(S, T, r, sigma, n_paths=1_000, seed=7)
    assert probability_of_touch(paths, S, "up") == pytest.approx(1.0)


def test_higher_vol_increases_touch_probability():
    S, T, r, barrier = 100, 1.0, 0.05, 130
    paths_low_vol = simulate_paths(S, T, r, sigma=0.15, n_paths=50_000, seed=7)
    paths_high_vol = simulate_paths(S, T, r, sigma=0.50, n_paths=50_000, seed=7)
    low = probability_of_touch(paths_low_vol, barrier, "up")
    high = probability_of_touch(paths_high_vol, barrier, "up")
    assert high > low
