import random
import datetime
from typing import Any
from decimal import ROUND_HALF_UP, Decimal
from math import exp, sqrt
from collections.abc import Iterable
from zoneinfo import ZoneInfo
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Currency, Stock, CurrencyAsset, Exchange, PriceCandle
from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
    STOCKS_UPDATE_INTERVAL_SECONDS
)

TIME_STEP_IN_YEARS = STOCKS_UPDATE_INTERVAL_SECONDS / (365 * 24 * 60 * 60)


def get_asset_timezone(asset: Stock | CurrencyAsset) -> datetime.tzinfo:
    if isinstance(asset, Stock):
        try:
            return ZoneInfo(asset.exchange.timezone)
        except Exception:
            return datetime.timezone.utc
    return datetime.timezone.utc


def _to_local_date(ts: datetime.datetime, tz: datetime.tzinfo) -> datetime.date:
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, datetime.timezone.utc)
    try:
        local_ts = ts.astimezone(tz)
    except Exception:
        local_ts = ts
    return local_ts.date()


def _floor_time_to_interval(
    ts: datetime.datetime,
    *,
    interval_minutes: int,
) -> datetime.datetime:
    total_minutes = ts.hour * 60 + ts.minute
    bucket_minutes = (total_minutes // interval_minutes) * interval_minutes
    bucket_hour = bucket_minutes // 60
    bucket_minute = bucket_minutes % 60
    return ts.replace(hour=bucket_hour, minute=bucket_minute, second=0, microsecond=0)


def get_candles_for_range(
    asset: Stock | CurrencyAsset,
    *,
    start_at: datetime.datetime,
    end_at: datetime.datetime,
    interval_minutes: int,
) -> list[dict[str, Any]]:
    candles_qs = PriceCandle.objects.filter(
        asset=asset,
        interval_minutes=interval_minutes,
        start_at__gte=start_at,
        start_at__lte=end_at,
    ).order_by("start_at")

    return [
        {
            "x": candle.start_at.isoformat(),
            "o": float(candle.open_price),
            "h": float(candle.high_price),
            "l": float(candle.low_price),
            "c": float(candle.close_price),
        }
        for candle in candles_qs
    ]


def _get_bucket_start(
    asset: Stock | CurrencyAsset,
    *,
    ts: datetime.datetime,
    interval_minutes: int,
) -> datetime.datetime:
    tz = get_asset_timezone(asset)
    local_ts = ts
    if timezone.is_naive(local_ts):
        local_ts = timezone.make_aware(local_ts, datetime.timezone.utc)
    try:
        local_ts = local_ts.astimezone(tz)
    except Exception:
        pass

    bucket_start_local = _floor_time_to_interval(local_ts, interval_minutes=interval_minutes)
    return bucket_start_local.astimezone(datetime.timezone.utc)


def upsert_price_candle(
    asset: Stock | CurrencyAsset,
    *,
    ts: datetime.datetime,
    price: Decimal,
    interval_minutes: int,
    source: str,
) -> None:
    start_at = _get_bucket_start(asset, ts=ts, interval_minutes=interval_minutes)

    candle, created = PriceCandle.objects.get_or_create(
        asset=asset,
        interval_minutes=interval_minutes,
        start_at=start_at,
        defaults={
            "open_price": price,
            "high_price": price,
            "low_price": price,
            "close_price": price,
            "volume": 1,
            "source": source,
        },
    )

    if not created:
        candle.high_price = max(candle.high_price, price)
        candle.low_price = min(candle.low_price, price)
        candle.close_price = price
        candle.volume = candle.volume + 1
        candle.source = source
        candle.save(update_fields=[
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "source",
        ])

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
def update_stock_prices_simulation(stocks: Iterable[Stock]) -> None:
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

@transaction.atomic
def update_currency_prices(currency_update_dict: dict[str, Any]) -> int:
    quotes = currency_update_dict.get('quotes', {})    
    timestamp = currency_update_dict.get('timestamp')
    if timestamp is None:
        raise ValueError("Missing timestamp in payload")
    

    base_currency = Currency.objects.get(is_base=True)
    base_currency_code = base_currency.code

    ts = datetime.datetime.fromtimestamp(
        float(timestamp), tz=datetime.timezone.utc
    )

    updated = 0

    for currency_asset in CurrencyAsset.objects.filter(is_active=True):
        quote_key = f"{base_currency_code}{currency_asset.symbol}"
        price_str = quotes.get(quote_key)
        if price_str is None:
            continue

        try:
            price = Decimal(price_str).quantize(Decimal("0.0001"))
        except Exception as e:
            raise ValueError(f"Invalid price for {quote_key}: {price_str}") from e
        
        for interval in (5, 60, 1440):
            upsert_price_candle(
                currency_asset,
                ts=ts,
                price=price,
                interval_minutes=interval,
                source="LIVE",
            )
        updated += 1


    # also add a price history for the base currency at price 1.0
    base_currency_asset = CurrencyAsset.objects.get(symbol=base_currency_code)
    for interval in (5, 60, 1440):
        upsert_price_candle(
            base_currency_asset,
            ts=ts,
            price=Decimal("1.0000"),
            interval_minutes=interval,
            source="LIVE",
        )

    updated += 1

    if updated == 0:
        raise ValueError("No prices created from payload")

    return updated


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