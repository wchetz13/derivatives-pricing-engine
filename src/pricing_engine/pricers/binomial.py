"""Cox-Ross-Rubinstein binomial tree for European and American options."""

from __future__ import annotations

import math

import numpy as np

from pricing_engine.models import (
    ExerciseStyle,
    Market,
    Option,
    OptionType,
    PriceResult,
    ValidationError,
)
from pricing_engine.pricers.base import ensure_supported


class BinomialPricer:
    """Recombining CRR tree, vectorized with NumPy (O(n^2) time, O(n) memory)."""

    name = "binomial"
    supported_styles = frozenset({ExerciseStyle.EUROPEAN, ExerciseStyle.AMERICAN})

    def __init__(self, steps: int = 500) -> None:
        if steps < 1:
            raise ValidationError("steps must be >= 1")
        self.steps = steps

    def price(self, option: Option, market: Market) -> PriceResult:
        ensure_supported(self, option)
        n = self.steps
        dt = option.maturity / n
        u = math.exp(market.volatility * math.sqrt(dt))
        d = 1.0 / u
        growth = math.exp((market.rate - market.dividend_yield) * dt)
        p = (growth - d) / (u - d)
        if not 0.0 < p < 1.0:
            raise ValidationError(
                f"risk-neutral probability {p:.4f} outside (0, 1); increase steps"
            )
        disc = math.exp(-market.rate * dt)
        sign = 1.0 if option.option_type is OptionType.CALL else -1.0
        american = option.style is ExerciseStyle.AMERICAN

        j = np.arange(n + 1)
        spots = market.spot * u ** (n - 2 * j)
        values = np.maximum(sign * (spots - option.strike), 0.0)
        for _ in range(n):
            values = disc * (p * values[:-1] + (1 - p) * values[1:])
            if american:
                spots = spots[:-1] / u
                values = np.maximum(values, sign * (spots - option.strike))
        return PriceResult(price=float(values[0]), model=self.name, diagnostics={"steps": n})
