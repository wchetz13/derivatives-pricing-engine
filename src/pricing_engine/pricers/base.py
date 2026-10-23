"""The pricer interface every model implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pricing_engine.models import ExerciseStyle, Market, Option, PriceResult


class UnsupportedContractError(ValueError):
    """Raised when a pricer is asked to price a contract it cannot handle."""


@runtime_checkable
class Pricer(Protocol):
    """Strategy interface for pricing models."""

    name: str
    supported_styles: frozenset[ExerciseStyle]

    def price(self, option: Option, market: Market) -> PriceResult: ...


def ensure_supported(pricer: Pricer, option: Option) -> None:
    if option.style not in pricer.supported_styles:
        raise UnsupportedContractError(
            f"{pricer.name} does not support {option.style.value} exercise"
        )
