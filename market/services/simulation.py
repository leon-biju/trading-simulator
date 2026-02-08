import random
from decimal import Decimal
from math import exp, sqrt
from collections.abc import Iterable

from django.utils import timezone

from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
)
from market.models import Asset
from .candles import upsert_price_candle

MINUTES_PER_YEAR = 365 * 24 * 60
DEFAULT_TIME_STEP_MINUTES = 5.0
MAX_TIME_STEP_MINUTES = 43200.0  # 30 days cap to prevent extreme jumps


def _calculate_time_step_years(asset: Asset) -> float:
    """
    Calculate the time step in years based on the time since the last price update.
    
    If the asset has no price history, uses the default 5-minute step.
    Otherwise, uses the actual elapsed time since the last update,
    capped at 30 days to prevent extreme price jumps.
    """
    last_update = asset.last_price_update()
    
    if last_update is None:
        time_step_minutes = DEFAULT_TIME_STEP_MINUTES
    else:
        elapsed = timezone.now() - last_update
        elapsed_minutes = elapsed.total_seconds() / 60
        # Use actual elapsed time, but cap at max to prevent extreme jumps
        time_step_minutes = min(max(elapsed_minutes, DEFAULT_TIME_STEP_MINUTES), MAX_TIME_STEP_MINUTES)
    
    return time_step_minutes / MINUTES_PER_YEAR


def update_asset_prices_simulation(assets: Iterable[Asset]) -> None:
    """
    Simulate Geometric Brownian Motion price updates.
    Creates/updates candles at 5-min, 60-min, and daily intervals.

    Each call generates a new price tick that:
    - Creates/updates current 5-min candle
    - Automatically aggregates into the current 60-min candle
    - Automatically aggregates into the current daily candle
    
    The time step is calculated based on the time since the last price update,
    allowing realistic price changes even if the simulation hasn't run for a while.
    """
    for asset in assets:
        # Calculate time step based on last price update for this asset
        time_step = _calculate_time_step_years(asset)
        drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * time_step
        vol = SIMULATION_SIGMA * sqrt(time_step)

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
