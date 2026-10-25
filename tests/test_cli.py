import json

import pytest

from pricing_engine.cli import main

BASE = ["--spot", "100", "--strike", "100", "--maturity", "1", "--rate", "0.05"]


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_price_default_model(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "price", *BASE, "--vol", "0.2")
    assert code == 0
    result = json.loads(out)
    assert result["model"] == "black_scholes"
    assert result["price"] == pytest.approx(10.450584, abs=1e-6)


def test_price_american_put_on_tree(capsys: pytest.CaptureFixture[str]) -> None:
    argv = [*BASE, "--vol", "0.2", "--type", "put", "--style", "american"]
    code, out, _ = run(capsys, "price", *argv, "--model", "binomial", "--steps", "200")
    assert code == 0
    assert json.loads(out)["diagnostics"] == {"steps": 200}


def test_monte_carlo_options(capsys: pytest.CaptureFixture[str]) -> None:
    argv = [*BASE, "--vol", "0.2", "--model", "monte_carlo", "--paths", "2000", "--seed", "5"]
    code, out, _ = run(capsys, "price", *argv)
    assert code == 0
    assert json.loads(out)["std_error"] > 0


def test_implied_vol(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "iv", *BASE, "--price", "10.450584")
    assert code == 0
    assert json.loads(out)["implied_volatility"] == pytest.approx(0.2, abs=1e-6)


def test_greeks_command(capsys: pytest.CaptureFixture[str]) -> None:
    argv = [*BASE, "--vol", "0.2", "--model", "binomial", "--steps", "300"]
    code, out, _ = run(capsys, "greeks", *argv)
    assert code == 0
    result = json.loads(out)
    assert result["method"] == "lattice"
    assert result["delta"] == pytest.approx(0.6368, abs=1e-3)


def test_models(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "models")
    assert code == 0
    assert "binomial" in json.loads(out)["models"]


@pytest.mark.parametrize(
    "argv",
    [
        ["price", *BASE, "--vol", "0.2", "--style", "american"],
        ["price", *BASE, "--vol", "-1"],
        ["price", *BASE, "--vol", "0.2", "--steps", "10"],
        ["iv", *BASE, "--price", "500"],
    ],
)
def test_errors_exit_2_with_json(capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
    code, _, err = run(capsys, *argv)
    assert code == 2
    assert "error" in json.loads(err)
