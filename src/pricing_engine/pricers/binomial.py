"""Cox-Ross-Rubinstein binomial tree for European and American options."""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from pricing_engine.models import (
    ExerciseStyle,
    Market,
    Option,
    OptionType,
    PriceResult,
    ValidationError,
)
from pricing_engine.pricers.base import ensure_supported

FloatArray = npt.NDArray[np.float64]


class BinomialPricer:
    """Recombining CRR tree, vectorized with NumPy (O(n^2) time, O(n) memory)."""

    name = "binomial"
    supported_styles = frozenset({ExerciseStyle.EUROPEAN, ExerciseStyle.AMERICAN})

    def __init__(self, steps: int = 500) -> None:
        if steps < 2:
            raise ValidationError("steps must be >= 2")
        self.steps = steps

    def price(self, option: Option, market: Market) -> PriceResult:
        ensure_supported(self, option)
        root = self._roll_back(option, market)[0]
        return PriceResult(price=float(root[0]), model=self.name, diagnostics={"steps": self.steps})

    def lattice_delta_gamma(self, option: Option, market: Market) -> tuple[float, float]:
        """Delta and gamma read from the tree's first two time steps.

        Bump-and-reprice is unreliable on a lattice: shifting the spot moves every node
        relative to the strike, so the price oscillates and a second difference amplifies
        that noise. Differencing node values inside one tree avoids the problem.
        """
        ensure_supported(self, option)
        _, step1, step2 = self._roll_back(option, market)
        s = market.spot
        u = self._up_factor(option, market)
        d = 1.0 / u
        delta = (step1[0] - step1[1]) / (s * u - s * d)
        delta_up = (step2[0] - step2[1]) / (s * u * u - s)
        delta_down = (step2[1] - step2[2]) / (s - s * d * d)
        gamma = (delta_up - delta_down) / (0.5 * (s * u * u - s * d * d))
        return float(delta), float(gamma)

    def _up_factor(self, option: Option, market: Market) -> float:
        return math.exp(market.volatility * math.sqrt(option.maturity / self.steps))

    def _roll_back(
        self, option: Option, market: Market
    ) -> tuple[FloatArray, FloatArray, FloatArray]:
        """Backward induction; returns node values at steps 0, 1, and 2."""
        n = self.steps
        dt = option.maturity / n
        u = self._up_factor(option, market)
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
        saved: dict[int, FloatArray] = {}
        for step in range(n - 1, -1, -1):
            values = disc * (p * values[:-1] + (1 - p) * values[1:])
            if american:
                spots = spots[:-1] / u
                values = np.maximum(values, sign * (spots - option.strike))
            if step <= 2:
                saved[step] = values
        return saved[0], saved[1], saved[2]
