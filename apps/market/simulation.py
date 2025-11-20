from decimal import Decimal
import random
from math import exp, sqrt 
from apps.market.models import PriceHistory
from config.constants import (
    MARKET_UPDATE_INTERVAL_SECONDS, 
    SIMULATION_SIGMA, 
    SIMULATION_MU,
    SIMULATION_INITIAL_PRICE_RANGE)

TIME_STEP_IN_YEARS = MARKET_UPDATE_INTERVAL_SECONDS / (365 * 24 * 60 * 60)

def update_stock_prices_simulation(stocks):
    # Simulate price updates for the given stocks

    new_stocks_prices_list = []

    for stock in stocks:
        last_price = stock.get_latest_price()
        if last_price is None:
            # If no prior price exists, assign a random starting price between 50 and 250
            last_price = Decimal(random.uniform(*SIMULATION_INITIAL_PRICE_RANGE)).quantize(Decimal('0.0001'))


            # --- Geometric Brownian Motion Calculation ---
        drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * TIME_STEP_IN_YEARS
        shock = SIMULATION_SIGMA * sqrt(TIME_STEP_IN_YEARS) * random.gauss(0, 1)

        price_change_factor = exp(drift + shock)

        new_price = Decimal(last_price * Decimal(price_change_factor)).quantize(Decimal('0.0001'))

        new_stocks_prices_list.append(
            PriceHistory(
                asset=stock,
                price=new_price,
                source='SIMULATION'
            )
        )

    if new_stocks_prices_list:
        PriceHistory.objects.bulk_create(new_stocks_prices_list)

def update_currency_prices_simulation(currencies):
    # Simulate price updates for the given currency
    for currency in currencies:
        # Logic to simulate price change
        pass