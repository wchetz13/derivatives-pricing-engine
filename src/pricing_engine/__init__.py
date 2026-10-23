"""derivatives-pricing-engine: pluggable option pricing models with a CLI and REST API."""

from pricing_engine.implied_vol import ImpliedVolError, implied_volatility
from pricing_engine.models import (
    ExerciseStyle,
    Market,
    Option,
    OptionType,
    PriceResult,
    ValidationError,
)
from pricing_engine.registry import available_models, get_pricer

__version__ = "0.1.0"

__all__ = [
    "ExerciseStyle",
    "ImpliedVolError",
    "Market",
    "Option",
    "OptionType",
    "PriceResult",
    "ValidationError",
    "available_models",
    "get_pricer",
    "implied_volatility",
]
