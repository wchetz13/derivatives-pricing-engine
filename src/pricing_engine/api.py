"""REST API built on FastAPI. Run with: uvicorn pricing_engine.api:app"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pricing_engine import __version__
from pricing_engine.implied_vol import ImpliedVolError, implied_volatility
from pricing_engine.models import ExerciseStyle, Market, Option, OptionType, ValidationError
from pricing_engine.pricers import BlackScholesPricer, UnsupportedContractError
from pricing_engine.registry import MODEL_OPTION_NAMES, available_models, get_pricer

app = FastAPI(
    title="Derivatives Pricing Engine",
    version=__version__,
    description="Price vanilla options, compute Greeks, and solve for implied volatility.",
)

Positive = Annotated[float, Field(gt=0)]


class ContractIn(BaseModel):
    spot: Positive
    strike: Positive
    maturity: Positive = Field(description="Years to expiry")
    rate: float = 0.0
    volatility: Positive = 0.2
    dividend_yield: Annotated[float, Field(ge=0)] = 0.0
    option_type: OptionType = OptionType.CALL
    style: ExerciseStyle = ExerciseStyle.EUROPEAN

    def to_domain(self) -> tuple[Option, Market]:
        return (
            Option(self.strike, self.maturity, self.option_type, self.style),
            Market(self.spot, self.rate, self.volatility, self.dividend_yield),
        )


class PriceIn(ContractIn):
    model: Literal["black_scholes", "binomial", "monte_carlo"] = "black_scholes"
    steps: Annotated[int, Field(ge=1, le=10_000)] | None = None
    paths: Annotated[int, Field(ge=2, le=2_000_000)] | None = None
    seed: int | None = None
    antithetic: bool | None = None
    control_variate: bool | None = None


class ImpliedVolIn(ContractIn):
    price: Positive


@app.exception_handler(ValidationError)
@app.exception_handler(UnsupportedContractError)
@app.exception_handler(ImpliedVolError)
async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/models")
def models() -> dict[str, list[str]]:
    return {"models": available_models()}


@app.post("/price")
def price(body: PriceIn) -> dict[str, Any]:
    option, market = body.to_domain()
    kwargs = {k: v for k in MODEL_OPTION_NAMES if (v := getattr(body, k)) is not None}
    return asdict(get_pricer(body.model, **kwargs).price(option, market))


@app.post("/greeks")
def greeks(body: ContractIn) -> dict[str, float]:
    option, market = body.to_domain()
    return asdict(BlackScholesPricer().greeks(option, market))


@app.post("/implied-vol")
def implied_vol(body: ImpliedVolIn) -> dict[str, float]:
    option, market = body.to_domain()
    return {"implied_volatility": implied_volatility(body.price, option, market)}
