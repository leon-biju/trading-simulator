import datetime
import random
from decimal import Decimal
from math import exp, sqrt

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from config.constants import (
    SIMULATION_INITIAL_PRICE_RANGE,
    SIMULATION_MU,
    SIMULATION_SIGMA,
)
from market.models import Asset, PriceCandle
from market.services.candles import get_asset_timezone


class Command(BaseCommand):
    help = "Backfill simulated OHLC candles for specified assets."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--ticker",
            nargs="+",
            required=True,
            help="One or more ticker symbols to backfill (e.g., --ticker AAPL GOOGL).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days to backfill (default: 365).",
        )
        parser.add_argument(
            "--intraday-days",
            type=int,
            default=7,
            help="Days from today to generate intraday candles (default: 7).",
        )
        parser.add_argument(
            "--interval-minutes",
            type=int,
            default=5,
            help="Intraday interval in minutes (default: 5).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing candle history for specified assets before backfilling.",
        )

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        tickers = options["ticker"]
        days = options["days"]
        intraday_days = options["intraday_days"]
        interval_minutes = options["interval_minutes"]
        reset = options["reset"]

        # Validate all tickers exist before proceeding
        assets = []
        missing_tickers = []
        for ticker in tickers:
            asset = Asset.objects.select_related("currency", "exchange").filter(ticker=ticker).first()
            if asset is None:
                missing_tickers.append(ticker)
            else:
                assets.append(asset)

        if missing_tickers:
            raise CommandError(
                f"The following tickers do not exist: {', '.join(missing_tickers)}"
            )

        if reset:
            deleted_count, _ = PriceCandle.objects.filter(asset__in=assets).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Cleared {deleted_count} existing candles for specified assets."
                )
            )

        now = timezone.now()
        start_date = (now - datetime.timedelta(days=days - 1)).date()
        intraday_start_date = (now - datetime.timedelta(days=intraday_days - 1)).date()

        batch: list[PriceCandle] = []
        batch_size = 4000

        for asset in assets:
            tz = get_asset_timezone(asset)
            latest_candle = PriceCandle.objects.filter(
                asset=asset,
                interval_minutes=1440,
            ).order_by("-start_at").first()
            if latest_candle:
                current_price = latest_candle.close_price
            else:
                current_price = Decimal(random.uniform(*SIMULATION_INITIAL_PRICE_RANGE)).quantize(Decimal("0.0001"))

            day = start_date
            while day <= now.date():
                if day.weekday() >= 5:
                    day += datetime.timedelta(days=1)
                    continue
                open_time = asset.exchange.open_time
                close_time = asset.exchange.close_time
                open_dt = datetime.datetime.combine(day, open_time, tzinfo=tz)
                close_dt = datetime.datetime.combine(day, close_time, tzinfo=tz)
                if close_dt <= open_dt:
                    close_dt += datetime.timedelta(days=1)

                if day >= intraday_start_date:
                    (
                        current_price,
                        daily_candle,
                        hourly_candles,
                        intraday_candles,
                    ) = self._generate_intraday_candles(
                        asset,
                        current_price,
                        open_dt,
                        close_dt,
                        interval_minutes,
                    )

                    batch.append(daily_candle)
                    batch.extend(hourly_candles)
                    batch.extend(intraday_candles)
                else:
                    daily_candle, current_price = self._generate_daily_candle(
                        asset,
                        current_price,
                        day,
                        tz,
                    )
                    batch.append(daily_candle)

                if len(batch) >= batch_size:
                    PriceCandle.objects.bulk_create(batch, ignore_conflicts=True)
                    batch.clear()

                day += datetime.timedelta(days=1)

        if batch:
            PriceCandle.objects.bulk_create(batch, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. Generated OHLC candles for {len(assets)} asset(s): {', '.join(tickers)}"
            )
        )

    def _generate_daily_candle(
        self,
        asset: Asset,
        current_price: Decimal,
        day: datetime.date,
        tz: datetime.tzinfo,
    ) -> tuple[PriceCandle, Decimal]:
        time_step = 1 / 365
        drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * time_step
        shock = SIMULATION_SIGMA * sqrt(time_step) * random.gauss(0, 1)
        price_change_factor = exp(drift + shock)

        open_price = current_price
        close_price = (open_price * Decimal(price_change_factor)).quantize(Decimal("0.0001"))

        intraday_vol = SIMULATION_SIGMA * sqrt(time_step / 6)
        high_factor = exp(abs(random.gauss(0, intraday_vol)))
        low_factor = exp(-abs(random.gauss(0, intraday_vol)))
        high_price = (open_price * Decimal(high_factor)).quantize(Decimal("0.0001"))
        low_price = (open_price * Decimal(low_factor)).quantize(Decimal("0.0001"))
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        start_at = datetime.datetime.combine(day, datetime.time(0, 0), tzinfo=tz).astimezone(
            datetime.timezone.utc
        )

        candle = PriceCandle(
            asset=asset,
            interval_minutes=1440,
            start_at=start_at,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=self._estimate_volume(asset, scale=1440),
            source="SIMULATION",
        )

        return candle, close_price

    def _generate_intraday_candles(
        self,
        asset: Asset,
        current_price: Decimal,
        open_dt: datetime.datetime,
        close_dt: datetime.datetime,
        interval_minutes: int,
    ) -> tuple[Decimal, PriceCandle, list[PriceCandle], list[PriceCandle]]:
        time_step = interval_minutes / (365 * 24 * 60)
        drift = (SIMULATION_MU - 0.5 * SIMULATION_SIGMA**2) * time_step
        vol = SIMULATION_SIGMA * sqrt(time_step)

        intraday_candles: list[PriceCandle] = []
        hourly_buckets: dict[datetime.datetime, dict[str, Decimal | int]] = {}

        daily_open = current_price
        daily_high = current_price
        daily_low = current_price
        daily_volume = 0

        cursor = open_dt
        while cursor <= close_dt:
            open_price = current_price
            shock = vol * random.gauss(0, 1)
            price_change_factor = exp(drift + shock)
            close_price = (open_price * Decimal(price_change_factor)).quantize(Decimal("0.0001"))

            intraday_vol = SIMULATION_SIGMA * sqrt(time_step / 4)
            high_factor = exp(abs(random.gauss(0, intraday_vol)))
            low_factor = exp(-abs(random.gauss(0, intraday_vol)))
            high_price = (open_price * Decimal(high_factor)).quantize(Decimal("0.0001"))
            low_price = (open_price * Decimal(low_factor)).quantize(Decimal("0.0001"))
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)

            candle_volume = self._estimate_volume(asset, scale=interval_minutes)
            daily_volume += candle_volume
            daily_high = max(daily_high, high_price)
            daily_low = min(daily_low, low_price)

            candle_start = cursor.astimezone(datetime.timezone.utc)
            intraday_candles.append(
                PriceCandle(
                    asset=asset,
                    interval_minutes=interval_minutes,
                    start_at=candle_start,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=candle_volume,
                    source="SIMULATION",
                )
            )

            hour_bucket_start = cursor.replace(minute=0, second=0, microsecond=0)
            bucket = hourly_buckets.get(hour_bucket_start)
            if bucket is None:
                hourly_buckets[hour_bucket_start] = {
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": candle_volume,
                }
            else:
                bucket["high"] = max(bucket["high"], high_price)
                bucket["low"] = min(bucket["low"], low_price)
                bucket["close"] = close_price
                bucket["volume"] = int(bucket["volume"]) + candle_volume

            current_price = close_price
            cursor += datetime.timedelta(minutes=interval_minutes)

        daily_close = current_price
        daily_start = datetime.datetime.combine(open_dt.date(), datetime.time(0, 0), tzinfo=open_dt.tzinfo)
        daily_candle = PriceCandle(
            asset=asset,
            interval_minutes=1440,
            start_at=daily_start.astimezone(datetime.timezone.utc),
            open_price=daily_open,
            high_price=daily_high,
            low_price=daily_low,
            close_price=daily_close,
            volume=daily_volume,
            source="SIMULATION",
        )

        hourly_candles = [
            PriceCandle(
                asset=asset,
                interval_minutes=60,
                start_at=hour_start.astimezone(datetime.timezone.utc),
                open_price=bucket["open"],
                high_price=bucket["high"],
                low_price=bucket["low"],
                close_price=bucket["close"],
                volume=int(bucket["volume"]),
                source="SIMULATION",
            )
            for hour_start, bucket in sorted(hourly_buckets.items())
        ]

        return current_price, daily_candle, hourly_candles, intraday_candles

    def _estimate_volume(self, asset: Asset, *, scale: int) -> int:
        base = 100_000 if scale >= 1440 else 10_000
        return random.randint(int(base * 0.5), int(base * 1.5))
