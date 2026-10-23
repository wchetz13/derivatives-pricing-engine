"""Implied volatility: Newton-Raphson with a bracketed Brent fallback."""

from __future__ import annotations

import math

from scipy.optimize import brentq

from pricing_engine.models import ExerciseStyle, Market, Option, OptionType
from pricing_engine.pricers.black_scholes import BlackScholesPricer

_BS = BlackScholesPricer()
VOL_LOWER, VOL_UPPER = 1e-6, 5.0


class ImpliedVolError(ValueError):
    """Raised when no volatility reproduces the target price."""


def no_arbitrage_bounds(option: Option, market: Market) -> tuple[float, float]:
    """Model-free lower and upper bounds on a European option price."""
    t = option.maturity
    fwd_spot = market.spot * math.exp(-market.dividend_yield * t)
    pv_strike = option.strike * math.exp(-market.rate * t)
    if option.option_type is OptionType.CALL:
        return max(fwd_spot - pv_strike, 0.0), fwd_spot
    return max(pv_strike - fwd_spot, 0.0), pv_strike


def implied_volatility(
    target_price: float,
    option: Option,
    market: Market,
    tol: float = 1e-10,
    max_iter: int = 50,
) -> float:
    """Return sigma such that Black-Scholes(sigma) == target_price.

    The ``volatility`` field of ``market`` is used only as the Newton starting guess.
    """
    if option.style is not ExerciseStyle.EUROPEAN:
        raise ImpliedVolError("implied volatility is only defined here for European options")
    lower, upper = no_arbitrage_bounds(option, market)
    if not lower < target_price < upper:
        raise ImpliedVolError(
            f"price {target_price:.6f} outside no-arbitrage bounds ({lower:.6f}, {upper:.6f})"
        )

    def objective(sigma: float) -> float:
        return _BS.price(option, market.with_volatility(sigma)).price - target_price

    sigma = market.volatility
    for _ in range(max_iter):
        diff = objective(sigma)
        if abs(diff) < tol:
            return sigma
        vega = _BS.greeks(option, market.with_volatility(sigma)).vega
        if vega < 1e-8:
            break
        step = sigma - diff / vega
        if not VOL_LOWER < step < VOL_UPPER:
            break
        sigma = step

    return float(brentq(objective, VOL_LOWER, VOL_UPPER, xtol=tol))
