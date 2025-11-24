import random
import datetime
from decimal import ROUND_HALF_UP, Decimal
from math import exp, sqrt
from typing import Optional, Tuple
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Currency, Stock, CurrencyAsset, Exchange, PriceHistory
from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
    STOCKS_UPDATE_INTERVAL_SECONDS
)

TIME_STEP_IN_YEARS = STOCKS_UPDATE_INTERVAL_SECONDS / (365 * 24 * 60 * 60)

def round_to_two_dp(value: Decimal) -> Decimal:
    return value.quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)


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

    #also add a price history for the base currency at price 1.0
    base_currency_asset = CurrencyAsset.objects.get(symbol=base_currency_code)
    new_currency_prices_list.append(
        PriceHistory(
            asset=base_currency_asset,
            timestamp=datetime.datetime.fromtimestamp(int(timestamp), tz=datetime.timezone.utc),
            price=Decimal('1.0000'),
            source='LIVE'
        )
    )

    if new_currency_prices_list:
        PriceHistory.objects.bulk_create(new_currency_prices_list)

    return f"Updated prices for {len(new_currency_prices_list)} currency assets."


def get_fx_rate(from_currency_code: str, to_currency_code: str) -> Decimal | None:
    # Get the latest FX rate between two currencies
    try:
        from_currencyasset = CurrencyAsset.objects.get(symbol=from_currency_code)
        to_currencyasset = CurrencyAsset.objects.get(symbol=to_currency_code)
    except CurrencyAsset.DoesNotExist:
        return None

    from_rate = from_currencyasset.get_latest_price()
    to_rate = to_currencyasset.get_latest_price()

    if from_rate is None or to_rate is None:
        return None

    exchange_rate = Decimal(to_rate / from_rate)
    return exchange_rate

def get_fx_conversion(
    from_currency_code: str,
    to_currency_code: str,
    from_amount: Optional[Decimal] = None,
    to_amount: Optional[Decimal] = None,
) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
    # Returns (from_amount, to_amount, error)

    if (from_amount is None and to_amount is None) or (from_amount is not None and to_amount is not None):
        return (None, None, "SPECIFY_EITHER_FROM_OR_TO_AMOUNT")



    exchange_rate = get_fx_rate(from_currency_code, to_currency_code)
    if exchange_rate is None:
        return (None, None, "UNSUPPORTED_CURRENCY_FOR_FX")

    if from_amount is not None:
        if from_amount <= 0:
            return (None, None, "INVALID_FROM_AMOUNT")
        calculated_to_amount = round_to_two_dp(from_amount * exchange_rate)
        return (from_amount, calculated_to_amount, None)
    else: # to_amount is not None
        if to_amount <= 0:
            return (None, None, "INVALID_TO_AMOUNT")
        calculated_from_amount = round_to_two_dp(to_amount / exchange_rate)
        return (calculated_from_amount, to_amount, None)