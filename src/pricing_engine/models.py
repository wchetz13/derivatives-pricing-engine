"""Core domain objects: option contracts, market data, and pricing results.

All objects are immutable and validate their inputs at construction, so pricers
can assume they always receive well-formed data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class ExerciseStyle(str, Enum):
    EUROPEAN = "european"
    AMERICAN = "american"


class ValidationError(ValueError):
    """Raised when a contract or market input is invalid."""


@dataclass(frozen=True, slots=True)
class Option:
    """A vanilla option contract.

    Attributes:
        strike: Strike price K (> 0).
        maturity: Time to expiry T in years (> 0).
        option_type: Call or put.
        style: European or American exercise.
    """

    strike: float
    maturity: float
    option_type: OptionType = OptionType.CALL
    style: ExerciseStyle = ExerciseStyle.EUROPEAN

    def __post_init__(self) -> None:
        if not self.strike > 0:
            raise ValidationError(f"strike must be positive, got {self.strike}")
        if not self.maturity > 0:
            raise ValidationError(f"maturity must be positive, got {self.maturity}")

    def payoff(self, spot: float) -> float:
        """Intrinsic value at a given underlying price."""
        if self.option_type is OptionType.CALL:
            return max(spot - self.strike, 0.0)
        return max(self.strike - spot, 0.0)


@dataclass(frozen=True, slots=True)
class Market:
    """Market state for a single underlying.

    Attributes:
        spot: Current underlying price S (> 0).
        rate: Continuously compounded risk-free rate r.
        volatility: Annualized volatility sigma (> 0).
        dividend_yield: Continuous dividend yield q (>= 0).
    """

    spot: float
    rate: float
    volatility: float
    dividend_yield: float = 0.0

    def __post_init__(self) -> None:
        if not self.spot > 0:
            raise ValidationError(f"spot must be positive, got {self.spot}")
        if not self.volatility > 0:
            raise ValidationError(f"volatility must be positive, got {self.volatility}")
        if self.dividend_yield < 0:
            raise ValidationError(f"dividend_yield must be >= 0, got {self.dividend_yield}")

    def with_spot(self, spot: float) -> Market:
        return Market(spot, self.rate, self.volatility, self.dividend_yield)

    def with_volatility(self, volatility: float) -> Market:
        return Market(self.spot, self.rate, volatility, self.dividend_yield)

    def with_rate(self, rate: float) -> Market:
        return Market(self.spot, rate, self.volatility, self.dividend_yield)


@dataclass(frozen=True, slots=True)
class PriceResult:
    """Output of a pricer.

    Attributes:
        price: Present value of the option.
        model: Name of the model that produced the price.
        std_error: Standard error for stochastic models, else None.
        diagnostics: Model-specific metadata (steps, paths, etc.).
    """

    price: float
    model: str
    std_error: float | None = None
    diagnostics: dict[str, float | int | str] = field(default_factory=dict)
