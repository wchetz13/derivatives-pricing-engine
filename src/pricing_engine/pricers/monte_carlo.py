"""Monte Carlo pricing under geometric Brownian motion with optional variance reduction."""

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


class MonteCarloPricer:
    """European pricer with a terminal-price control variate and optional antithetic variates.

    The control variate is on by default. Antithetic variates are off by default: once the
    control variate removes the payoff's linear component, the residual is roughly symmetric
    in the shock, so antithetic pairs become positively correlated and widen the error.

    Results are reproducible for a given seed.
    """

    name = "monte_carlo"
    supported_styles = frozenset({ExerciseStyle.EUROPEAN})

    def __init__(
        self,
        paths: int = 100_000,
        seed: int | None = 0,
        antithetic: bool = False,
        control_variate: bool = True,
    ) -> None:
        if paths < 2 or (antithetic and paths % 2):
            raise ValidationError("paths must be >= 2 (and even when antithetic is enabled)")
        self.paths = paths
        self.seed = seed
        self.antithetic = antithetic
        self.control_variate = control_variate

    def price(self, option: Option, market: Market) -> PriceResult:
        ensure_supported(self, option)
        rng = np.random.default_rng(self.seed)
        t, sigma = option.maturity, market.volatility
        half = self.paths // 2
        if self.antithetic:
            z = rng.standard_normal(half)
            z = np.concatenate([z, -z])
        else:
            z = rng.standard_normal(self.paths)
        drift = (market.rate - market.dividend_yield - 0.5 * sigma**2) * t
        terminal = market.spot * np.exp(drift + sigma * math.sqrt(t) * z)

        disc = math.exp(-market.rate * t)
        sign = 1.0 if option.option_type is OptionType.CALL else -1.0
        samples = disc * np.maximum(sign * (terminal - option.strike), 0.0)

        diagnostics: dict[str, float | int | str] = {
            "paths": self.paths,
            "antithetic": str(self.antithetic).lower(),
        }
        if self.control_variate:
            control = disc * terminal
            control_mean = market.spot * math.exp(-market.dividend_yield * t)
            cov = np.cov(samples, control)
            beta = cov[0, 1] / cov[1, 1]
            samples = samples - beta * (control - control_mean)
            diagnostics["control_beta"] = float(beta)

        if self.antithetic:
            # Antithetic pairs are dependent, so the standard error is computed on pair means.
            pair_means = 0.5 * (samples[:half] + samples[half:])
            std_error = pair_means.std(ddof=1) / math.sqrt(half)
        else:
            std_error = samples.std(ddof=1) / math.sqrt(self.paths)
        return PriceResult(
            price=float(samples.mean()),
            model=self.name,
            std_error=float(std_error),
            diagnostics=diagnostics,
        )
