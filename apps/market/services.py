import random
import datetime
from decimal import Decimal
from math import exp, sqrt
from django.db import transaction
from django.utils import timezone
from .models import Currency, Stock, CurrencyAsset, Exchange, PriceHistory
from .api_access import get_currency_layer_data
from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
    STOCKS_UPDATE_INTERVAL_SECONDS
)

TIME_STEP_IN_YEARS = STOCKS_UPDATE_INTERVAL_SECONDS / (365 * 24 * 60 * 60)

@transaction.atomic
def create_stock_asset(symbol: str, name: str, exchange: Exchange, currency: Currency) -> Stock:
    stock = Stock.objects.create(
        asset_type='STOCK',
        symbol=symbol,
        name=name,
        currency=currency,
        exchange=exchange
    )
    return stock


@transaction.atomic
def create_currency_asset(symbol: str, name: str) -> CurrencyAsset:
    #All currency assets are priced in the base currency.

    base_currency = Currency.objects.get(is_base=True)
    currency_asset = CurrencyAsset.objects.create(
        asset_type='CURRENCY',
        symbol=symbol,
        name=name,
        currency=base_currency
    )
    return currency_asset


@transaction.atomic
def update_stock_prices_simulation(stocks: list[Stock]):
    # Simulate price updates for the given stocks

    new_stocks_prices_list = []

    for stock in stocks:
        last_price = stock.get_latest_price()
        if last_price is None:
            last_price = Decimal(random.uniform(*SIMULATION_INITIAL_PRICE_RANGE)).quantize(Decimal('0.0001'))


        # Geometric Brownian Motion calculation
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

@transaction.atomic
def update_currency_prices(currency_update_dict: dict) -> str:

    quotes = currency_update_dict.get('quotes', {})
    if not quotes:
        return "No currency quotes found in the data."

    new_currency_prices_list = []

    base_currency_code = Currency.objects.get(is_base=True).code
    timestamp = currency_update_dict.get('timestamp')

    for currency_asset in CurrencyAsset.objects.filter(is_active=True):
        quote_key = f"{base_currency_code}{currency_asset.symbol}"
        if quote_key in quotes:
            new_price = Decimal(quotes[quote_key]).quantize(Decimal('0.0001'))

            new_currency_prices_list.append(
                PriceHistory(
                    asset=currency_asset,
                    timestamp=datetime.datetime.fromtimestamp(int(timestamp), tz=datetime.timezone.utc),
                    price=new_price,
                    source='LIVE'
                )
            )

    if new_currency_prices_list:
        PriceHistory.objects.bulk_create(new_currency_prices_list)

    return f"Updated prices for {len(new_currency_prices_list)} currency assets."