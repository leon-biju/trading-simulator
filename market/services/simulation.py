from decimal import Decimal
import random
from math import exp, sqrt
from collections.abc import Iterable
from django.db import transaction
from django.utils import timezone
from ..models import Asset
from .candles import upsert_price_candle
from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
    STOCKS_UPDATE_INTERVAL_MINUTES
)

TIME_STEP_IN_YEARS = STOCKS_UPDATE_INTERVAL_MINUTES / (365 * 24 * 60)

@transaction.atomic
def update_stock_prices_simulation(stocks: Iterable[Asset]) -> None:
    # Simulate price updates for the given stocks

    for stock in stocks:
        last_price = stock.get_latest_price()
        if last_price is None:
            last_price = Decimal(random.uniform(*SIMULATION_INITIAL_PRICE_RANGE)).quantize(Decimal('0.0001'))


        # Geometric Brownian Motion calculation
        drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * TIME_STEP_IN_YEARS
        shock = SIMULATION_SIGMA * sqrt(TIME_STEP_IN_YEARS) * random.gauss(0, 1)

        price_change_factor = exp(drift + shock)

        new_price = Decimal(last_price * Decimal(price_change_factor)).quantize(Decimal('0.0001'))

        ts = timezone.now()
        for interval in (5, 60, 1440):
            upsert_price_candle(
                stock,
                ts=ts,
                price=new_price,
                interval_minutes=interval,
                source="SIMULATION",
            )
