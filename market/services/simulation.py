import random
from decimal import Decimal
from math import exp, sqrt
from collections.abc import Iterable
from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
)
from market.models import Asset
from .candles import upsert_price_candle


def update_asset_prices_simulation(assets: Iterable[Asset]) -> None:
    """
    Simulate GBM-based price updates for the given assets.
    Creates/updates candles at 5-min, 60-min, and daily intervals.

    Each call generates a new price tick that:
    - Creates a new 5-min candle or updates an existing one within the same bucket
    - Aggregates into the current 60-min candle
    - Aggregates into the current daily candle
    """
    time_step = 5 / (365 * 24 * 60)  # 5 minutes in years
    drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * time_step
    vol = SIMULATION_SIGMA * sqrt(time_step)

    for asset in assets:
        current_price = asset.get_latest_price()
        if current_price is None:
            current_price = Decimal(
                random.uniform(*SIMULATION_INITIAL_PRICE_RANGE)
            ).quantize(Decimal("0.0001"))

        # Generate new price using Geometric Brownian Motion
        shock = vol * random.gauss(0, 1)
        price_change_factor = exp(drift + shock)
        new_price = (current_price * Decimal(price_change_factor)).quantize(
            Decimal("0.0001")
        )

        # Generate intraday high/low variation for realistic candles
        intraday_vol = SIMULATION_SIGMA * sqrt(time_step / 4)
        high_factor = exp(abs(random.gauss(0, intraday_vol)))
        low_factor = exp(-abs(random.gauss(0, intraday_vol)))

        open_price = current_price
        close_price = new_price
        high_price = max(
            (open_price * Decimal(high_factor)).quantize(Decimal("0.0001")),
            open_price,
            close_price,
        )
        low_price = min(
            (open_price * Decimal(low_factor)).quantize(Decimal("0.0001")),
            open_price,
            close_price,
        )

        volume = random.randint(5_000, 15_000)

        # Upsert candles at all intervals - they aggregate naturally
        for interval in (5, 60, 1440):
            upsert_price_candle(
                asset=asset,
                interval_minutes=interval,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
            )
