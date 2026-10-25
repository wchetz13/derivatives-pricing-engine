import math

import pytest

from pricing_engine import ExerciseStyle, Market, Option, OptionType, ValidationError, get_pricer
from pricing_engine.pricers import (
    BinomialPricer,
    BlackScholesPricer,
    MonteCarloPricer,
    UnsupportedContractError,
)

BS = BlackScholesPricer()


def test_black_scholes_reference_values(market: Market, call: Option, put: Option) -> None:
    # Hull, Options Futures and Other Derivatives: S=K=100, r=5%, sigma=20%, T=1.
    assert BS.price(call, market).price == pytest.approx(10.450584, abs=1e-6)
    assert BS.price(put, market).price == pytest.approx(5.573526, abs=1e-6)


def test_black_scholes_rejects_american(market: Market, american_put: Option) -> None:
    with pytest.raises(UnsupportedContractError):
        BS.price(american_put, market)


def test_greeks_match_finite_differences(market: Market, call: Option) -> None:
    g = BS.greeks(call, market)
    h = 1e-4

    def price(m: Market, o: Option = call) -> float:
        return BS.price(o, m).price

    delta = (price(market.with_spot(100 + h)) - price(market.with_spot(100 - h))) / (2 * h)
    gamma = (
        price(market.with_spot(100 + h)) - 2 * price(market) + price(market.with_spot(100 - h))
    ) / h**2
    vega = (price(market.with_volatility(0.2 + h)) - price(market.with_volatility(0.2 - h))) / (
        2 * h
    )
    rho = (price(market.with_rate(0.05 + h)) - price(market.with_rate(0.05 - h))) / (2 * h)
    shorter = Option(call.strike, call.maturity - h, call.option_type)
    theta = (price(market, shorter) - price(market)) / h

    assert g.delta == pytest.approx(delta, rel=1e-6)
    assert g.gamma == pytest.approx(gamma, rel=1e-3)
    assert g.vega == pytest.approx(vega, rel=1e-6)
    assert g.rho == pytest.approx(rho, rel=1e-6)
    assert g.theta == pytest.approx(theta, rel=1e-3)


def test_put_greeks_signs(market: Market, put: Option) -> None:
    g = BS.greeks(put, market)
    assert -1 < g.delta < 0
    assert g.rho < 0
    assert g.gamma > 0
    assert g.vega > 0


@pytest.mark.parametrize("option_type", list(OptionType))
def test_binomial_converges_to_black_scholes(market: Market, option_type: OptionType) -> None:
    option = Option(100.0, 1.0, option_type)
    tree = BinomialPricer(steps=2000).price(option, market)
    assert tree.price == pytest.approx(BS.price(option, market).price, abs=5e-3)
    assert tree.diagnostics["steps"] == 2000


def test_american_put_has_early_exercise_premium(
    market: Market, put: Option, american_put: Option
) -> None:
    tree = BinomialPricer(steps=1000)
    assert tree.price(american_put, market).price > tree.price(put, market).price + 0.3


def test_american_call_without_dividends_equals_european(market: Market, call: Option) -> None:
    american = Option(100.0, 1.0, OptionType.CALL, ExerciseStyle.AMERICAN)
    tree = BinomialPricer(steps=500)
    assert tree.price(american, market).price == pytest.approx(tree.price(call, market).price)


def test_binomial_rejects_bad_configuration(market: Market, call: Option) -> None:
    with pytest.raises(ValidationError):
        BinomialPricer(steps=1)
    high_rate = Market(100.0, rate=2.0, volatility=0.01)
    with pytest.raises(ValidationError, match="increase steps"):
        BinomialPricer(steps=2).price(call, high_rate)


def test_monte_carlo_is_within_three_standard_errors(market: Market, call: Option) -> None:
    result = MonteCarloPricer(paths=200_000, seed=7).price(call, market)
    assert result.std_error is not None
    assert abs(result.price - BS.price(call, market).price) < 3 * result.std_error
    assert result.std_error < 0.02


def test_monte_carlo_is_reproducible(market: Market, put: Option) -> None:
    a = MonteCarloPricer(paths=10_000, seed=1).price(put, market)
    b = MonteCarloPricer(paths=10_000, seed=1).price(put, market)
    assert a == b


def test_monte_carlo_rejects_bad_paths() -> None:
    with pytest.raises(ValidationError):
        MonteCarloPricer(paths=1)
    with pytest.raises(ValidationError, match="even"):
        MonteCarloPricer(paths=3, antithetic=True)


def test_control_variate_beats_antithetic_and_plain(market: Market, call: Option) -> None:
    def std_error(**kwargs: bool) -> float:
        result = MonteCarloPricer(paths=100_000, seed=11, **kwargs).price(call, market)
        assert result.std_error is not None
        return result.std_error

    plain = std_error(control_variate=False)
    antithetic = std_error(control_variate=False, antithetic=True)
    control = std_error()
    both = std_error(antithetic=True)
    assert control < antithetic < plain
    assert control < both


def test_dividend_yield_lowers_call_value(market: Market, call: Option) -> None:
    with_div = Market(100.0, 0.05, 0.2, dividend_yield=0.03)
    assert BS.price(call, with_div).price < BS.price(call, market).price
    mc = MonteCarloPricer(paths=100_000, seed=3).price(call, with_div)
    assert mc.std_error is not None
    assert abs(mc.price - BS.price(call, with_div).price) < 3 * mc.std_error


def test_registry(market: Market, call: Option) -> None:
    assert get_pricer("binomial", steps=50).price(call, market).model == "binomial"
    with pytest.raises(ValidationError, match="unknown model"):
        get_pricer("nope")
    with pytest.raises(ValidationError, match="does not accept"):
        get_pricer("black_scholes", steps=10)


def test_deep_in_the_money_call_approaches_forward_intrinsic(market: Market) -> None:
    deep = Option(strike=1.0, maturity=1.0)
    expected = 100.0 - 1.0 * math.exp(-0.05)
    assert BS.price(deep, market).price == pytest.approx(expected, rel=1e-9)
