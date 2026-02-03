import datetime
from typing import Any
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.utils import timezone

from ..models import Asset, PriceCandle


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

    local_ts = local_ts.astimezone(tz)

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
