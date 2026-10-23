"""Name-based lookup of pricing models, so callers (CLI, API) never import concrete classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pricing_engine.models import ValidationError
from pricing_engine.pricers import BinomialPricer, BlackScholesPricer, MonteCarloPricer, Pricer

PricerFactory = Callable[..., Pricer]

# Every model-specific option any registered pricer accepts; callers forward these by name.
MODEL_OPTION_NAMES = ("steps", "paths", "seed", "antithetic", "control_variate")

_REGISTRY: dict[str, tuple[PricerFactory, frozenset[str]]] = {}


def register(name: str, factory: PricerFactory, options: frozenset[str] = frozenset()) -> None:
    """Register a pricer factory and the keyword options it accepts."""
    if name in _REGISTRY:
        raise ValueError(f"pricer {name!r} is already registered")
    _REGISTRY[name] = (factory, options)


def get_pricer(name: str, **kwargs: Any) -> Pricer:
    """Build a pricer by name. Options the model does not accept are rejected."""
    factory, options = _lookup(name)
    unknown = set(kwargs) - options
    if unknown:
        raise ValidationError(f"{name} does not accept options: {sorted(unknown)}")
    return factory(**kwargs)


def _lookup(name: str) -> tuple[PricerFactory, frozenset[str]]:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValidationError(f"unknown model {name!r}; available: {available_models()}") from None


def available_models() -> list[str]:
    return sorted(_REGISTRY)


register("black_scholes", BlackScholesPricer)
register("binomial", BinomialPricer, frozenset({"steps"}))
register(
    "monte_carlo", MonteCarloPricer, frozenset({"paths", "seed", "antithetic", "control_variate"})
)
