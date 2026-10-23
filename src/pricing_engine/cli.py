"""Command-line interface. Prints JSON so output can be piped into other tools."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

from pricing_engine.implied_vol import ImpliedVolError, implied_volatility
from pricing_engine.models import ExerciseStyle, Market, Option, OptionType, ValidationError
from pricing_engine.pricers import UnsupportedContractError
from pricing_engine.registry import MODEL_OPTION_NAMES, available_models, get_pricer


def _add_contract_args(parser: argparse.ArgumentParser, *, need_vol: bool) -> None:
    parser.add_argument("--spot", type=float, required=True)
    parser.add_argument("--strike", type=float, required=True)
    parser.add_argument("--maturity", type=float, required=True, help="years to expiry")
    parser.add_argument("--rate", type=float, default=0.0)
    parser.add_argument("--vol", type=float, required=need_vol, default=0.2)
    parser.add_argument("--dividend-yield", type=float, default=0.0)
    parser.add_argument("--type", choices=[t.value for t in OptionType], default="call")
    parser.add_argument("--style", choices=[s.value for s in ExerciseStyle], default="european")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pricing-engine", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    price = sub.add_parser("price", help="price an option")
    _add_contract_args(price, need_vol=True)
    price.add_argument("--model", choices=available_models(), default="black_scholes")
    price.add_argument("--steps", type=int, help="binomial tree steps")
    price.add_argument("--paths", type=int, help="Monte Carlo paths")
    price.add_argument("--seed", type=int, help="Monte Carlo seed")
    price.add_argument("--antithetic", action=argparse.BooleanOptionalAction)
    price.add_argument("--control-variate", action=argparse.BooleanOptionalAction)

    iv = sub.add_parser("iv", help="solve for implied volatility")
    _add_contract_args(iv, need_vol=False)
    iv.add_argument("--price", type=float, required=True, dest="target_price")

    sub.add_parser("models", help="list available models")
    return parser


def _contract(args: argparse.Namespace) -> tuple[Option, Market]:
    option = Option(args.strike, args.maturity, OptionType(args.type), ExerciseStyle(args.style))
    market = Market(args.spot, args.rate, args.vol, args.dividend_yield)
    return option, market


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "models":
        return {"models": available_models()}
    option, market = _contract(args)
    if args.command == "iv":
        return {"implied_volatility": implied_volatility(args.target_price, option, market)}
    model_kwargs = {k: v for k in MODEL_OPTION_NAMES if (v := getattr(args, k)) is not None}
    return asdict(get_pricer(args.model, **model_kwargs).price(option, market))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
    except (ValidationError, UnsupportedContractError, ImpliedVolError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
