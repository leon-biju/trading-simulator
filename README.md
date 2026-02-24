# Trading Simulator

A full-stack trading simulator built with Django, Celery, and PostgreSQL. Users receive virtual capital to trade equities across multiple global exchanges with simulated price movements, multi-currency wallets, live FX rates, and portfolio tracking.
Exchanges and Assets are stored in `market/data/` as jsons, and are fully customisable for the server admin.

---

## Features

- **Market simulation**: Geometric Brownian Motion price engine with configurable drift/volatility, generating OHLC candles at 5-min, 60-min, and daily intervals
- **Exchange-aware scheduling**: prices only tick during each exchange's real trading hours and timezone
- **Market and limit orders**: market orders fill immediately; limit orders queue and auto-execute when the price condition is met
- **Order reservations**: funds (buys) or shares (sells) are locked on placement to prevent over-commitment
- **Multi-currency wallets**: one wallet per supported currency, with atomic FX transfers at live exchange rates
- **Portfolio tracking**: weighted average cost basis, unrealized/realized P&L, and automated daily portfolio snapshots
- **Async task engine**: Celery workers handle price ticks, FX updates, order processing, snapshot generation, and stale order expiry
- **Configurable**: starting balance, tick interval, trading fees, simulation parameters, and others are modifiable in `config/constants.py`
- Orders are executed as soon as the market opens

---

## Apps

- **accounts**: user registration, authentication, and profile management
- **dashboard**: contains main dashboard page displaying portoflio and wallets information
- **market**: exchanges, assets, price candle generation, FX rates, and runs the price simulation
- **trading**: order placement/cancellation, order execution, position tracking, and portfolio snapshots
- **wallets**: multi-currency balances, transaction ledger, deposits, and FX transfers

---

## Price Simulation Model

The market engine uses **Geometric Brownian Motion (GBM)** to simulate realistic asset price movements. GBM is the same stochastic process that the Black-Scholes option pricing model uses, and it ensures prices are always positive and follows the log-normal distribution observed in real markets.

The continuous-time GBM stochastic differential equation is:

$$dS = \mu\, S\, dt + \sigma\, S\, dW$$


where $S$ is the asset price, $\mu$ is the annualised drift (expected return), $\sigma$ is the annualised volatility, and $dW$ is a Wiener process increment.

For discrete simulation steps the exact solution is used:

$$S_{t+\Delta t} = S_t \exp\!\left[\left(\mu - \tfrac{\sigma^2}{2}\right)\Delta t + \sigma\,\sqrt{\Delta t}\;Z\right]$$

where $\Delta t$ is the time step expressed in years and $Z \sim \mathcal{N}(0,1)$ is a standard normal random variable.

In code (`market/services/simulation.py`) the two terms are computed as:

| Symbol | Code | Meaning |
|---|---|---|
| $\left(\mu - \frac{\sigma^2}{2}\right)\Delta t$ | `drift` | Deterministic drift component (risk-adjusted) |
| $\sigma\sqrt{\Delta t}\;Z$ | `shock` | Random volatility component |

The $-\frac{\sigma^2}{2}$ correction  comes from [Itô's lemma](https://en.wikipedia.org/wiki/It%C3%B4%27s_lemma#Geometric_Brownian_motion)

Each tick, the simulation generates synthetic OHLC (open/high/low/close) candles at 5-minute, 60-minute, and daily intervals by drawing an independent $Z \sim \mathcal{N}(0,1)$ for each of the four prices.
*(Open and close are bounded by high and low, and high $\ge$ low)*

---

## Tech Stack

| | |
|---|---|
| **Backend** | Python 3.13, Django 5.2 |
| **Database** | PostgreSQL 16 |
| **Task Queue** | Celery 5.5 + Redis 7 |
| **Frontend** | Django Templates, Bootstrap 5 |
| **Containers** | Docker Compose |
| **FX Data** | [CurrencyLayer API](https://currencylayer.com/) |
| **Testing** | pytest, factory_boy |
| **Type Checking** | mypy, django-stubs |

---

## Setup

### Prerequisites

- Docker, Docker Compose
- A free [CurrencyLayer API key](https://currencylayer.com/signup/free)

### 1. Clone and configure

```bash
git clone https://github.com/username/trading-simulator.git
cd trading-simulator
```

Duplicate `example.env` to `.env.dev` and fill in the values. Do not change database credentials after the DB container has been created.

### 2. Build and start

```bash
docker-compose up --build --detach
```

This starts the following containers: `db` (Postgres), `redis`, `web` (Django on port 8000), `celery_worker`, `celery_beat`, and `pgadmin` (port 8080).

### 3. Run migrations

```bash
docker-compose exec web python manage.py migrate
```

### 4. Set up market data and create admin account

```bash
docker-compose exec web python manage.py setup_market_data
docker-compose exec web python manage.py createsuperuser
```

The `setup_market_data` wizard lets you choose currencies, loads exchanges and assets from bundled JSON data ( stored in market/data), and sets up FX rates. The wizard also lets you choose a base currency, which is used for currency conversion and internal calculations.

### 5. Access the application locally

- Application: [http://localhost:8000](http://localhost:8000)
- Django admin page: [http://localhost:8000/admin/](http://localhost:8000/admin/)
- pgAdmin: [http://localhost:8080](http://localhost:8080)


---

## Testing

```bash
# All tests
docker-compose exec web pytest

# Specific app
docker-compose exec web pytest wallets/

```

---

## Useful Commands

```bash
# Backfill price history for a specific list of assets
docker-compose exec web python manage.py backfill_asset_history --ticker AAPL GOOGL PLTR
```

---

## Configuration

Key parameters in `config/constants.py`:

| Constant | Default | Description |
|---|---|---|
| `STARTING_BALANCE` | 100,000 | Initial balance for new users (in base currency) |
| `MARKET_TICK_INTERVAL_MINUTES` | 5 | Price update frequency (Time between price movements)|
| `FX_RATES_UPDATE_INTERVAL_MINUTES` | 480 | FX rate retrieval interval|
| `ORDER_EXPIRY_DAYS` | 30 | Days before pending orders automatically expire |
| `SIMULATION_MU` | 0.08 | Annual drift coefficient |
| `SIMULATION_SIGMA` | 0.20 | Annual volatility coefficient |
| `TRADING_FEE_PERCENTAGE` | 0.001 | Commission per trade |

---

## License

MIT: see [LICENSE](LICENSE).