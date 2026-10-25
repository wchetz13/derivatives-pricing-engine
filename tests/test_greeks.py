import dataclasses

import pytest

from pricing_engine import (
    BumpSizes,
    ExerciseStyle,
    Market,
    Option,
    OptionType,
    ValidationError,
    compute_greeks,
    finite_difference_greeks,
)
from pricing_engine.pricers import BinomialPricer, BlackScholesPricer, Greeks, MonteCarloPricer

FIELDS = [f.name for f in dataclasses.fields(Greeks)]


def assert_close(actual: Greeks, expected: Greeks, rel: float) -> None:
    for name in FIELDS:
        assert getattr(actual, name) == pytest.approx(getattr(expected, name), rel=rel), name


@pytest.fixture
def exact(market: Market, call: Option) -> Greeks:
    return BlackScholesPricer().greeks(call, market)


def test_black_scholes_uses_closed_form(market: Market, call: Option, exact: Greeks) -> None:
    assert compute_greeks(call, market) == (exact, "analytic")


def test_finite_differences_reproduce_closed_form(
    market: Market, call: Option, exact: Greeks
) -> None:
    assert_close(finite_difference_greeks(BlackScholesPricer(), call, market), exact, rel=1e-3)


def test_lattice_greeks_match_black_scholes(market: Market, call: Option, exact: Greeks) -> None:
    greeks, method = compute_greeks(call, market, "binomial", steps=500)
    assert method == "lattice"
    assert_close(greeks, exact, rel=3e-3)


def test_bumped_gamma_on_a_tree_is_unreliable(market: Market, call: Option, exact: Greeks) -> None:
    """Why lattice gamma exists: bumping spot shifts nodes past the strike."""
    bumped = finite_difference_greeks(BinomialPricer(steps=500), call, market)
    lattice, _ = compute_greeks(call, market, "binomial", steps=500)
    assert abs(bumped.gamma / exact.gamma - 1) > 0.5
    assert abs(lattice.gamma / exact.gamma - 1) < 0.01


def test_monte_carlo_greeks_with_common_random_numbers(
    market: Market, call: Option, exact: Greeks
) -> None:
    greeks, method = compute_greeks(call, market, "monte_carlo", paths=200_000, seed=1)
    assert method == "finite_difference"
    assert_close(greeks, exact, rel=0.02)


def test_monte_carlo_greeks_require_a_seed(market: Market, call: Option) -> None:
    with pytest.raises(ValidationError, match="seed"):
        finite_difference_greeks(MonteCarloPricer(paths=1000, seed=None), call, market)


def test_american_put_greeks_converge(market: Market, american_put: Option) -> None:
    coarse, _ = compute_greeks(american_put, market, "binomial", steps=500)
    fine, _ = compute_greeks(american_put, market, "binomial", steps=4000)
    assert_close(coarse, fine, rel=2e-3)
    assert -1 < fine.delta < 0
    assert fine.gamma > 0
    assert fine.rho < 0


def test_american_put_delta_is_more_negative_than_european(
    market: Market, put: Option, american_put: Option
) -> None:
    american, _ = compute_greeks(american_put, market, "binomial", steps=1000)
    european, _ = compute_greeks(put, market, "binomial", steps=1000)
    assert american.delta < european.delta


def test_vega_bump_shrinks_for_low_volatility(call: Option) -> None:
    low_vol = Market(100.0, 0.05, volatility=0.004)
    greeks = finite_difference_greeks(
        BlackScholesPricer(), call, low_vol, BumpSizes(volatility=0.01)
    )
    exact = BlackScholesPricer().greeks(call, low_vol)
    assert greeks.vega == pytest.approx(exact.vega, rel=1e-2)


def test_theta_step_is_capped_for_short_maturities(market: Market) -> None:
    short = Option(strike=100.0, maturity=1 / 730, option_type=OptionType.CALL)
    greeks = finite_difference_greeks(BlackScholesPricer(), short, market)
    assert greeks.theta < 0


def test_greeks_reject_unsupported_styles(market: Market) -> None:
    american_call = Option(100.0, 1.0, OptionType.CALL, ExerciseStyle.AMERICAN)
    with pytest.raises(ValueError, match="american"):
        compute_greeks(american_call, market, "monte_carlo")
