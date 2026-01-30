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

from .models import Asset, Currency, Exchange, FXRate, PriceCandle
from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
    STOCKS_UPDATE_INTERVAL_SECONDS
)

TIME_STEP_IN_YEARS = STOCKS_UPDATE_INTERVAL_SECONDS / (365 * 24 * 60 * 60)


def get_asset_timezone(asset: Asset) -> datetime.tzinfo:
    try:
        return ZoneInfo(asset.exchange.timezone)
    except Exception:
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
    asset: Asset,
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
    asset: Asset,
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
    asset: Asset,
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
def create_stock_asset(symbol: str, name: str, exchange: Exchange, currency: Currency) -> Asset:
    stock = Asset.objects.create(
        asset_type='STOCK',
        ticker=symbol,
        name=name,
        currency=currency,
        exchange=exchange,
    )
    return stock


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

@transaction.atomic
def update_currency_prices(currency_update_dict: dict[str, Any]) -> int:
    quotes = currency_update_dict.get('quotes', {})
    timestamp = currency_update_dict.get('timestamp')
    if timestamp is None:
        raise ValueError("Missing timestamp in payload")

    base_currency = Currency.objects.get(is_base=True)
    base_currency_code = base_currency.code

    updated = 0

    for currency_code in quotes.keys():
        quote_key = f"{base_currency_code}{currency_code}"
        price_str = quotes.get(quote_key)
        if price_str is None:
            continue

        try:
            price = Decimal(price_str).quantize(Decimal("0.000001"))
        except Exception as e:
            raise ValueError(f"Invalid price for {quote_key}: {price_str}") from e

        FXRate.objects.update_or_create(
            base_currency=base_currency,
            target_currency=Currency.objects.get(code=currency_code),
            defaults={"rate": price},
        )
        updated += 1

    # Also update the base currency rate to itself
    FXRate.objects.update_or_create(
        base_currency=base_currency,
        target_currency=base_currency,
        defaults={"rate": Decimal("1.0")},
    )
    updated += 1

    if updated == 0:
        raise ValueError("No rates created from payload")

    return updated


def get_fx_rate(from_currency_code: str, to_currency_code: str) -> Decimal | None:
    if from_currency_code == to_currency_code:
        return Decimal("1.0")

    try:
        from_currency = Currency.objects.get(code=from_currency_code)
    except Currency.DoesNotExist:
        raise LookupError(f"Currency not found: {from_currency_code}")
    
    try:
        to_currency = Currency.objects.get(code=to_currency_code)
    except Currency.DoesNotExist:
        raise LookupError(f"Currency not found: {to_currency_code}")

    from_rate = FXRate.objects.filter(
        base_currency__is_base=True,
        target_currency=from_currency,
    ).first()

    to_rate = FXRate.objects.filter(
        base_currency__is_base=True,
        target_currency=to_currency,
    ).first()

    if from_rate is None:
        raise LookupError(f"FX rate not found for currency: {from_currency_code}")
    if to_rate is None:
        raise LookupError(f"FX rate not found for currency: {to_currency_code}")

    return to_rate.rate / from_rate.rate

    
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