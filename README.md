# Trading Simulator

A full-stack stock trading simulator built with Django, Celery, and PostgreSQL. Users get play money to trade equities across multiple global exchanges with simulated price movements, multi-currency wallets, live FX rates, and portfolio tracking. The bundled market data in `market/data/` (exchanges and assets) is fully customisable — the included set is just a starting point.

---

## Features

- **Market simulation** — Geometric Brownian Motion price engine with configurable drift/volatility, generating OHLC candles at 5-min, 60-min, and daily intervals
- **Exchange-aware scheduling** — prices only tick during each exchange's real trading hours and timezone
- **Market and limit orders** — market orders fill immediately; limit orders queue and auto-execute when the price condition is met
- **Order reservations** — funds (buys) or shares (sells) are locked on placement to prevent over-commitment
- **Multi-currency wallets** — one wallet per supported currency, with atomic FX transfers at live exchange rates
- **Portfolio tracking** — weighted average cost basis, unrealized/realized P&L, and automated daily portfolio snapshots
- **Async task engine** — Celery workers handle price ticks, FX updates, order processing, snapshot generation, and stale order expiry
- **Configurable** — starting balance, tick interval, trading fees, simulation parameters, and more are all tuneable in `config/constants.py`

---

## Apps

- **accounts** — user registration, authentication, and profile management (home currency preference)
- **dashboard** — portfolio overview showing positions, P&L, cash balances, and recent trades
- **market** — exchanges, assets, price candle generation, FX rates, and the GBM simulation engine
- **trading** — order placement/cancellation, execution engine, position tracking, and portfolio snapshots
- **wallets** — multi-currency balances, transaction ledger, deposits, and FX transfers

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

- Docker and Docker Compose
- A free [CurrencyLayer API key](https://currencylayer.com/signup/free)

### 1. Clone and configure

```bash
git clone https://github.com/username/trading-simulator.git
cd trading-simulator
```

Duplicate `example.env` to `.env` and fill in the values. Do not change database credentials after the DB container has been created.

### 2. Build and start

```bash
docker-compose up --build --detach
```

This starts 6 containers: `db` (Postgres), `redis`, `web` (Django on port 8000), `celery_worker`, `celery_beat`, and `pgadmin` (port 8080).

### 3. Run migrations

```bash
docker-compose exec web python manage.py migrate
```

### 4. Set up market data

```bash
docker-compose exec web python manage.py setup_market_data
```

This interactive wizard lets you choose currencies, loads exchanges and assets from bundled JSON data, and seeds FX rates.

### 5. Access the app

- Application: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Admin: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- pgAdmin: [http://127.0.0.1:8080](http://127.0.0.1:8080)

Register a new account to get started. Each user receives a starting balance and wallets for all configured currencies.

---

## Testing

```bash
# All tests
docker-compose exec web pytest

# Specific app
docker-compose exec web pytest wallets/tests/

# With coverage
docker-compose exec web pytest --cov
```

---

## Useful Commands

```bash
# Set up market data
docker-compose exec web python manage.py setup_market_data

# Backfill price history for an asset
docker-compose exec web python manage.py backfill_asset_history --ticker AAPL

# Apply migrations
docker-compose exec web python manage.py migrate

# Type checking
docker-compose exec web mypy .
```

---

## Configuration

Key parameters in `config/constants.py`:

| Constant | Default | Description |
|---|---|---|
| `STARTING_BALANCE` | 100,000 | Initial balance for new users (base currency) |
| `MARKET_TICK_INTERVAL_MINUTES` | 5 | Price update frequency |
| `FX_RATES_UPDATE_INTERVAL_MINUTES` | 480 | FX rate refresh interval |
| `ORDER_EXPIRY_DAYS` | 30 | Days before pending orders expire |
| `SIMULATION_MU` | 0.08 | Annual drift coefficient |
| `SIMULATION_SIGMA` | 0.20 | Annual volatility coefficient |
| `TRADING_FEE_PERCENTAGE` | 0.001 | Commission per trade |

---

## License

MIT — see [LICENSE](LICENSE).