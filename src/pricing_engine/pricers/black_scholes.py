"""Closed-form Black-Scholes-Merton pricing and analytic Greeks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm

from pricing_engine.models import ExerciseStyle, Market, Option, OptionType, PriceResult
from pricing_engine.pricers.base import ensure_supported


@dataclass(frozen=True, slots=True)
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


def _d1_d2(option: Option, market: Market) -> tuple[float, float]:
    s, k, t = market.spot, option.strike, option.maturity
    r, q, sigma = market.rate, market.dividend_yield, market.volatility
    vol_sqrt_t = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma**2) * t) / vol_sqrt_t
    return d1, d1 - vol_sqrt_t


class BlackScholesPricer:
    """Analytic Black-Scholes-Merton model for European options with dividend yield."""

    name = "black_scholes"
    supported_styles = frozenset({ExerciseStyle.EUROPEAN})

    def price(self, option: Option, market: Market) -> PriceResult:
        ensure_supported(self, option)
        d1, d2 = _d1_d2(option, market)
        s, k, t = market.spot, option.strike, option.maturity
        df_r = math.exp(-market.rate * t)
        df_q = math.exp(-market.dividend_yield * t)
        if option.option_type is OptionType.CALL:
            value = s * df_q * norm.cdf(d1) - k * df_r * norm.cdf(d2)
        else:
            value = k * df_r * norm.cdf(-d2) - s * df_q * norm.cdf(-d1)
        return PriceResult(price=float(value), model=self.name)

    def greeks(self, option: Option, market: Market) -> Greeks:
        """Analytic Greeks. Vega and rho are per 1.00 change; theta is per year."""
        ensure_supported(self, option)
        d1, d2 = _d1_d2(option, market)
        s, k, t = market.spot, option.strike, option.maturity
        r, q, sigma = market.rate, market.dividend_yield, market.volatility
        df_r, df_q = math.exp(-r * t), math.exp(-q * t)
        pdf_d1 = float(norm.pdf(d1))

        gamma = df_q * pdf_d1 / (s * sigma * math.sqrt(t))
        vega = s * df_q * pdf_d1 * math.sqrt(t)
        decay = -s * df_q * pdf_d1 * sigma / (2 * math.sqrt(t))
        if option.option_type is OptionType.CALL:
            delta = df_q * norm.cdf(d1)
            theta = decay - r * k * df_r * norm.cdf(d2) + q * s * df_q * norm.cdf(d1)
            rho = k * t * df_r * norm.cdf(d2)
        else:
            delta = -df_q * norm.cdf(-d1)
            theta = decay + r * k * df_r * norm.cdf(-d2) - q * s * df_q * norm.cdf(-d1)
            rho = -k * t * df_r * norm.cdf(-d2)
        return Greeks(float(delta), float(gamma), float(vega), float(theta), float(rho))
