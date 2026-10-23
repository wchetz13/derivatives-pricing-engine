import dataclasses

import pytest

from pricing_engine import Market, Option, OptionType, ValidationError


@pytest.mark.parametrize(
    "kwargs",
    [{"strike": 0.0, "maturity": 1.0}, {"strike": 100.0, "maturity": -1.0}],
)
def test_option_rejects_invalid_inputs(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        Option(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"spot": 0.0, "rate": 0.0, "volatility": 0.2},
        {"spot": 100.0, "rate": 0.0, "volatility": 0.0},
        {"spot": 100.0, "rate": 0.0, "volatility": 0.2, "dividend_yield": -0.01},
    ],
)
def test_market_rejects_invalid_inputs(kwargs: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        Market(**kwargs)


def test_payoff() -> None:
    assert Option(100.0, 1.0, OptionType.CALL).payoff(110.0) == 10.0
    assert Option(100.0, 1.0, OptionType.CALL).payoff(90.0) == 0.0
    assert Option(100.0, 1.0, OptionType.PUT).payoff(90.0) == 10.0


def test_domain_objects_are_immutable(market: Market) -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        market.spot = 1.0  # type: ignore[misc]


def test_market_copy_helpers(market: Market) -> None:
    assert market.with_spot(50.0).spot == 50.0
    assert market.with_rate(0.01).rate == 0.01
    assert market.with_volatility(0.3).volatility == 0.3
    assert market.spot == 100.0
