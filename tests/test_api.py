import pytest
from fastapi.testclient import TestClient

from pricing_engine.api import app

client = TestClient(app)
CONTRACT = {"spot": 100, "strike": 100, "maturity": 1, "rate": 0.05, "volatility": 0.2}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models() -> None:
    assert client.get("/models").json() == {"models": ["binomial", "black_scholes", "monte_carlo"]}


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        ({}, 10.4506),
        ({"model": "binomial", "steps": 1000}, 10.4486),
        ({"model": "monte_carlo", "paths": 100000, "seed": 1}, 10.45),
    ],
)
def test_price(extra: dict[str, object], expected: float) -> None:
    response = client.post("/price", json=CONTRACT | extra)
    assert response.status_code == 200
    assert response.json()["price"] == pytest.approx(expected, abs=0.05)


def test_greeks() -> None:
    body = client.post("/greeks", json=CONTRACT).json()
    assert set(body) == {"delta", "gamma", "vega", "theta", "rho"}
    assert body["delta"] == pytest.approx(0.6368, abs=1e-4)


def test_implied_vol_round_trip() -> None:
    price = client.post("/price", json=CONTRACT).json()["price"]
    body = client.post("/implied-vol", json=CONTRACT | {"price": price, "volatility": 0.5})
    assert body.json()["implied_volatility"] == pytest.approx(0.2, abs=1e-8)


@pytest.mark.parametrize(
    "payload",
    [
        CONTRACT | {"spot": -1},
        CONTRACT | {"model": "not_a_model"},
        CONTRACT | {"model": "monte_carlo", "paths": 3, "antithetic": True},
        CONTRACT | {"model": "black_scholes", "steps": 10},
        CONTRACT | {"style": "american"},
    ],
)
def test_invalid_requests_return_422(payload: dict[str, object]) -> None:
    response = client.post("/price", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_implied_vol_outside_bounds_returns_422() -> None:
    response = client.post("/implied-vol", json=CONTRACT | {"price": 500})
    assert response.status_code == 422
