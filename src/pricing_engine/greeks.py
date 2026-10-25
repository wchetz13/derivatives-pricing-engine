"""Greeks for any registered model.

- Black-Scholes: closed form.
- Binomial: delta and gamma from the lattice itself; vega, rho, and theta by bump-and-reprice.
- Monte Carlo: bump-and-reprice with common random numbers. Every bumped revaluation
  reuses the same seed, so sampling noise cancels in the differences instead of swamping them.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Literal

from pricing_engine.models import Market, Option, ValidationError
from pricing_engine.pricers import (
    BinomialPricer,
    BlackScholesPricer,
    Greeks,
    MonteCarloPricer,
    Pricer,
)
from pricing_engine.registry import get_pricer

Method = Literal["analytic", "lattice", "finite_difference"]


@dataclass(frozen=True, slots=True)
class BumpSizes:
    """Finite-difference step sizes.

    Attributes:
        spot: Relative spot bump (0.01 = 1% of spot).
        volatility: Absolute volatility bump (0.01 = one vol point).
        rate: Absolute rate bump (0.0001 = one basis point).
        time: Time bump in years (one day by default).
    """

    spot: float = 0.01
    volatility: float = 0.01
    rate: float = 1e-4
    time: float = 1 / 365


def finite_difference_greeks(
    pricer: Pricer, option: Option, market: Market, bumps: BumpSizes | None = None
) -> Greeks:
    """Central-difference Greeks by revaluing the option under bumped inputs.

    Theta uses a one-sided step forward in calendar time (shorter maturity), matching the
    analytic convention: value change per year as time passes.
    """
    if isinstance(pricer, MonteCarloPricer) and pricer.seed is None:
        raise ValidationError("Monte Carlo Greeks need a fixed seed (common random numbers)")
    b = bumps or BumpSizes()

    def pv(m: Market = market, o: Option = option) -> float:
        return pricer.price(o, m).price

    base = pv()
    h = market.spot * b.spot
    up, down = pv(market.with_spot(market.spot + h)), pv(market.with_spot(market.spot - h))
    dv = min(b.volatility, market.volatility / 2)
    vega = (
        pv(market.with_volatility(market.volatility + dv))
        - pv(market.with_volatility(market.volatility - dv))
    ) / (2 * dv)
    rho = (
        pv(market.with_rate(market.rate + b.rate)) - pv(market.with_rate(market.rate - b.rate))
    ) / (2 * b.rate)
    dt = min(b.time, option.maturity / 2)
    theta = (pv(o=dataclasses.replace(option, maturity=option.maturity - dt)) - base) / dt
    return Greeks(
        delta=(up - down) / (2 * h),
        gamma=(up - 2 * base + down) / h**2,
        vega=vega,
        theta=theta,
        rho=rho,
    )


def compute_greeks(
    option: Option, market: Market, model: str = "black_scholes", **model_options: Any
) -> tuple[Greeks, Method]:
    """Greeks from the named model, using the most accurate method that model supports."""
    pricer = get_pricer(model, **model_options)
    if isinstance(pricer, BlackScholesPricer):
        return pricer.greeks(option, market), "analytic"
    greeks = finite_difference_greeks(pricer, option, market)
    if isinstance(pricer, BinomialPricer):
        delta, gamma = pricer.lattice_delta_gamma(option, market)
        return dataclasses.replace(greeks, delta=delta, gamma=gamma), "lattice"
    return greeks, "finite_difference"
