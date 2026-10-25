# Changelog

## 0.2.0 — 2026-10-24

### Added
- Greeks for every model via `compute_greeks`, `pricing-engine greeks`, and `POST /greeks`:
  - Black-Scholes: closed form.
  - Binomial: delta and gamma read from the lattice; vega, rho, and theta by bump-and-reprice. This works for American options.
  - Monte Carlo: bump-and-reprice with common random numbers.
- `finite_difference_greeks` and configurable `BumpSizes` for any `Pricer`.
- `BinomialPricer.lattice_delta_gamma`.

### Changed
- `POST /greeks` accepts the same model parameters as `/price` and returns `model` and `method` alongside the Greeks.
- `BinomialPricer` now requires at least 2 steps, which lattice gamma needs.

## 0.1.0 — 2026-10-23

- Initial release: Black-Scholes, binomial, and Monte Carlo pricers; implied volatility; CLI; REST API; CI.
