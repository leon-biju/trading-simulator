import datetime
from typing import Any
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.utils import timezone

from ..models import Asset, PriceCandle


def get_asset_timezone(asset: Asset) -> ZoneInfo:
    try:
        return ZoneInfo(asset.exchange.timezone)
    except Exception:
        return ZoneInfo("UTC")


def _floor_time_to_interval(
    dt: datetime.datetime,
    interval_minutes: int,
    tz: ZoneInfo,
) -> datetime.datetime:
    """
    Floor a datetime to the start of its interval bucket in the given timezone.
    Returns the bucket start time in UTC.
    """
    local_dt = dt.astimezone(tz)
    midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    total_minutes = int((local_dt - midnight).total_seconds() // 60)
    bucket_minutes = (total_minutes // interval_minutes) * interval_minutes
    floored_local = midnight + datetime.timedelta(minutes=bucket_minutes)
    return floored_local.astimezone(datetime.timezone.utc)


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
    ts: datetime.datetime,
    interval_minutes: int,
) -> datetime.datetime:
    """
    Get the bucket start time for a given timestamp and interval.
    """
    tz = get_asset_timezone(asset)
    if timezone.is_naive(ts):
        ts = timezone.make_aware(ts, datetime.timezone.utc)
    return _floor_time_to_interval(ts, interval_minutes, tz)


def upsert_price_candle(
    asset: Asset,
    interval_minutes: int,
    open_price: Decimal,
    high_price: Decimal,
    low_price: Decimal,
    close_price: Decimal,
    volume: int,
    ts: datetime.datetime | None = None,
) -> PriceCandle:
    """
    Create or update a price candle for the given asset and interval.

    For new candles: uses the provided OHLC values.
    For existing candles: preserves open, updates high/low/close, adds volume.

    Args:
        asset: The asset to create/update candle for
        interval_minutes: Candle interval (5, 60, 1440)
        open_price: Opening price for this tick
        high_price: High price for this tick
        low_price: Low price for this tick
        close_price: Closing price for this tick
        volume: Volume for this tick
        ts: Timestamp for the candle (defaults to now)

    Returns:
        The created or updated PriceCandle
    """
    if ts is None:
        ts = timezone.now()

    candle_start = _get_bucket_start(asset, ts, interval_minutes)

    candle, created = PriceCandle.objects.get_or_create(
        asset=asset,
        interval_minutes=interval_minutes,
        start_at=candle_start,
        defaults={
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "close_price": close_price,
            "volume": volume,
            "source": "SIMULATION",
        },
    )

    if not created:
        # Aggregate: expand high/low range, update close, accumulate volume
        candle.high_price = max(candle.high_price, high_price)
        candle.low_price = min(candle.low_price, low_price)
        candle.close_price = close_price
        candle.volume += volume
        candle.save(update_fields=["high_price", "low_price", "close_price", "volume"])

    return candle
