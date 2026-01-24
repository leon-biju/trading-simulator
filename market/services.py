import random
import datetime
from decimal import ROUND_HALF_UP, Decimal
from math import exp, sqrt
from collections.abc import Iterable
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
def update_stock_prices_simulation(stocks: Iterable[Stock]):
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
def update_currency_prices(currency_update_dict: dict) -> int:
    quotes = currency_update_dict.get('quotes', {})
    if not quotes:
        raise ValueError("No currency quotes in payload")
    
    timestamp = currency_update_dict.get('timestamp')
    if timestamp is None:
        raise ValueError("Missing timestamp in payload")
    

    base_currency = Currency.objects.get(is_base=True)
    base_currency_code = base_currency.code

    ts = datetime.datetime.fromtimestamp(
        float(timestamp), tz=datetime.timezone.utc
    )

    new_currency_prices = []

    for currency_asset in CurrencyAsset.objects.filter(is_active=True):
        quote_key = f"{base_currency_code}{currency_asset.symbol}"
        price_str = quotes.get(quote_key)
        if price_str is None:
            continue

        try:
            price = Decimal(price_str).quantize(Decimal("0.0001"))
        except Exception as e:
            raise ValueError(f"Invalid price for {quote_key}: {price_str}") from e
        
        new_currency_prices.append(
            PriceHistory(
                asset=currency_asset,
                timestamp=ts,
                price=price,
                source="LIVE",
            )
        )


    # also add a price history for the base currency at price 1.0
    base_currency_asset = CurrencyAsset.objects.get(symbol=base_currency_code)
    new_currency_prices.append(
        PriceHistory(
            asset=base_currency_asset,
            timestamp=ts,
            price=Decimal('1.0000'),
            source='LIVE'
        )
    )

    if not new_currency_prices:
        raise ValueError("No prices created from payload")
    
    PriceHistory.objects.bulk_create(new_currency_prices)

    return len(new_currency_prices)


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

    exchange_rate = to_rate / from_rate
    return exchange_rate

def get_fx_conversion(
    from_currency_code: str,
    to_currency_code: str,
    *,
    from_amount: Decimal | None = None,
    to_amount: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    if (from_amount is None) == (to_amount is None):
        raise ValueError("Specify exactly one of from_amount or to_amount")

    exchange_rate = get_fx_rate(from_currency_code, to_currency_code)
    if exchange_rate is None:
        raise LookupError(f"Unsupported currency pair: {from_currency_code}{to_currency_code}")

    if from_amount is not None:
        if from_amount <= 0:
            raise ValueError("from_amount must be > 0")
        return from_amount, round_to_two_dp(from_amount * exchange_rate)
    
    assert to_amount is not None

    if to_amount <= 0:
        raise ValueError("to_amount must be > 0")
    return round_to_two_dp(to_amount / exchange_rate), to_amount