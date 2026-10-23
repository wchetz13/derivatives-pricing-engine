import pytest

from pricing_engine import ExerciseStyle, Market, Option, OptionType


@pytest.fixture
def market() -> Market:
    return Market(spot=100.0, rate=0.05, volatility=0.2)


@pytest.fixture
def call() -> Option:
    return Option(strike=100.0, maturity=1.0, option_type=OptionType.CALL)


@pytest.fixture
def put() -> Option:
    return Option(strike=100.0, maturity=1.0, option_type=OptionType.PUT)


@pytest.fixture
def american_put() -> Option:
    return Option(100.0, 1.0, OptionType.PUT, ExerciseStyle.AMERICAN)
