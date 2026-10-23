"""Property-based tests: no-arbitrage relationships that must hold for any valid inputs."""

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from pricing_engine import Market, Option, OptionType, implied_volatility
from pricing_engine.implied_vol import no_arbitrage_bounds
from pricing_engine.pricers import BlackScholesPricer

BS = BlackScholesPricer()

spots = st.floats(min_value=10.0, max_value=500.0)
strikes = st.floats(min_value=10.0, max_value=500.0)
maturities = st.floats(min_value=0.05, max_value=5.0)
rates = st.floats(min_value=-0.02, max_value=0.15)
vols = st.floats(min_value=0.05, max_value=1.0)
divs = st.floats(min_value=0.0, max_value=0.08)


@given(spots, strikes, maturities, rates, vols, divs)
def test_put_call_parity(s: float, k: float, t: float, r: float, v: float, q: float) -> None:
    market = Market(s, r, v, q)
    call = BS.price(Option(k, t, OptionType.CALL), market).price
    put = BS.price(Option(k, t, OptionType.PUT), market).price
    assert math.isclose(call - put, s * math.exp(-q * t) - k * math.exp(-r * t), abs_tol=1e-8)


@given(spots, strikes, maturities, rates, vols, divs, st.sampled_from(list(OptionType)))
def test_price_within_no_arbitrage_bounds(
    s: float, k: float, t: float, r: float, v: float, q: float, kind: OptionType
) -> None:
    option, market = Option(k, t, kind), Market(s, r, v, q)
    lower, upper = no_arbitrage_bounds(option, market)
    price = BS.price(option, market).price
    assert lower - 1e-9 <= price <= upper + 1e-9


@given(spots, strikes, maturities, rates, vols)
def test_call_increases_with_spot_and_vol(s: float, k: float, t: float, r: float, v: float) -> None:
    option, market = Option(k, t), Market(s, r, v)
    base = BS.price(option, market).price
    assert BS.price(option, market.with_spot(s * 1.01)).price >= base - 1e-12
    assert BS.price(option, market.with_volatility(v * 1.01)).price >= base - 1e-12


@settings(max_examples=200)
@given(
    st.floats(min_value=50.0, max_value=150.0),
    maturities,
    st.floats(min_value=0.0, max_value=0.1),
    vols,
    st.sampled_from(list(OptionType)),
)
def test_implied_vol_round_trip(k: float, t: float, r: float, v: float, kind: OptionType) -> None:
    option, market = Option(k, t, kind), Market(100.0, r, v)
    price = BS.price(option, market).price
    lower, _ = no_arbitrage_bounds(option, market)
    # Prices indistinguishable from intrinsic value carry no volatility information.
    if price - lower < 1e-6:
        return
    solved = implied_volatility(price, option, market.with_volatility(0.5))
    assert math.isclose(solved, v, rel_tol=1e-5)
