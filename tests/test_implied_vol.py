import pytest

from pricing_engine import ImpliedVolError, Market, Option, implied_volatility
from pricing_engine.pricers import BlackScholesPricer


def test_recovers_known_volatility(market: Market, call: Option) -> None:
    price = BlackScholesPricer().price(call, market.with_volatility(0.35)).price
    assert implied_volatility(price, call, market) == pytest.approx(0.35, abs=1e-8)


def test_falls_back_to_brent_from_a_bad_starting_guess(market: Market) -> None:
    far_otm = Option(strike=300.0, maturity=0.25)
    price = BlackScholesPricer().price(far_otm, market.with_volatility(0.9)).price
    solved = implied_volatility(price, far_otm, market.with_volatility(0.01))
    assert solved == pytest.approx(0.9, abs=1e-6)


@pytest.mark.parametrize("price", [0.0, 100.0, 250.0])
def test_rejects_prices_outside_no_arbitrage_bounds(
    price: float, market: Market, call: Option
) -> None:
    with pytest.raises(ImpliedVolError, match="no-arbitrage"):
        implied_volatility(price, call, market)


def test_rejects_american(market: Market, american_put: Option) -> None:
    with pytest.raises(ImpliedVolError, match="European"):
        implied_volatility(5.0, american_put, market)
