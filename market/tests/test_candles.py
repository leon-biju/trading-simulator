# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call
# mypy: disable-error-code=assignment

import datetime
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.utils import timezone

from market.models import PriceCandle, Asset
from market.services.candles import upsert_price_candle
from market.tests.factories import AssetFactory, ExchangeFactory


class TestUpsertPriceCandle:
    """Tests for the upsert_price_candle function."""

    def test_creates_new_candle_when_none_exists(self, db):
        """Test that a new candle is created when no candle exists for the bucket."""
        asset: Asset = AssetFactory()

        mock_time = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 2),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=mock_time):
            candle = upsert_price_candle(
                asset=asset,
                interval_minutes=5,
                open_price=Decimal("100.0000"),
                high_price=Decimal("101.0000"),
                low_price=Decimal("99.0000"),
                close_price=Decimal("100.5000"),
                volume=1000,
            )

        assert PriceCandle.objects.filter(asset=asset, interval_minutes=5).count() == 1
        assert candle.open_price == Decimal("100.0000")
        assert candle.high_price == Decimal("101.0000")
        assert candle.low_price == Decimal("99.0000")
        assert candle.close_price == Decimal("100.5000")
        assert candle.volume == 1000

    def test_upsert_within_same_5min_bucket_does_not_create_new_candle(self, db):
        """
        Test that upserting 1 minute later within the same 5-min bucket
        updates the existing candle instead of creating a new one.
        """
        asset: Asset = AssetFactory()

        # First upsert at 10:02
        time_1 = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 2),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=time_1):
            upsert_price_candle(
                asset=asset,
                interval_minutes=5,
                open_price=Decimal("100.0000"),
                high_price=Decimal("101.0000"),
                low_price=Decimal("99.0000"),
                close_price=Decimal("100.5000"),
                volume=1000,
            )

        # Second upsert at 10:03 (1 minute later, same bucket)
        time_2 = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 3),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=time_2):
            candle = upsert_price_candle(
                asset=asset,
                interval_minutes=5,
                open_price=Decimal("100.5000"),
                high_price=Decimal("102.0000"),
                low_price=Decimal("100.0000"),
                close_price=Decimal("101.5000"),
                volume=1500,
            )

        # Should still be only 1 candle
        assert PriceCandle.objects.filter(asset=asset, interval_minutes=5).count() == 1

        # Open should be preserved from first upsert
        assert candle.open_price == Decimal("100.0000")
        # High should be max of both
        assert candle.high_price == Decimal("102.0000")
        # Low should be min of both
        assert candle.low_price == Decimal("99.0000")
        # Close should be from second upsert
        assert candle.close_price == Decimal("101.5000")
        # Volume should be accumulated
        assert candle.volume == 2500

    def test_upsert_after_5min_creates_new_candle(self, db):
        """
        Test that upserting 5 minutes later creates a new candle
        because it falls into a different bucket.
        """
        asset: Asset = AssetFactory()

        # First upsert at 10:02 (bucket: 10:00-10:05)
        time_1 = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 2),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=time_1):
            candle_1 = upsert_price_candle(
                asset=asset,
                interval_minutes=5,
                open_price=Decimal("100.0000"),
                high_price=Decimal("101.0000"),
                low_price=Decimal("99.0000"),
                close_price=Decimal("100.5000"),
                volume=1000,
            )

        # Second upsert at 10:07 (bucket: 10:05-10:10)
        time_2 = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 7),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=time_2):
            candle_2 = upsert_price_candle(
                asset=asset,
                interval_minutes=5,
                open_price=Decimal("100.5000"),
                high_price=Decimal("102.0000"),
                low_price=Decimal("100.0000"),
                close_price=Decimal("101.5000"),
                volume=1500,
            )

        # Should now have 2 candles
        assert PriceCandle.objects.filter(asset=asset, interval_minutes=5).count() == 2

        # Each candle should have its own values
        assert candle_1.close_price == Decimal("100.5000")
        assert candle_2.open_price == Decimal("100.5000")
        assert candle_2.close_price == Decimal("101.5000")


class TestCandleAggregation:
    """Tests for candle aggregation across different intervals."""

    def test_5min_candles_aggregate_into_60min_candle(self, db):
        """
        Test that multiple 5-min updates within the same hour
        aggregate correctly into a single 60-min candle.
        """
        asset: Asset = AssetFactory()

        # Simulate 3 price updates within the same hour (10:00-11:00)
        updates = [
            # (time, open, high, low, close, volume)
            (datetime.datetime(2025, 11, 14, 10, 2), "100.00", "101.00", "99.00", "100.50", 1000),
            (datetime.datetime(2025, 11, 14, 10, 17), "100.50", "103.00", "100.00", "102.00", 1200),
            (datetime.datetime(2025, 11, 14, 10, 32), "102.00", "102.50", "98.00", "99.00", 800),
        ]

        for dt, open_p, high_p, low_p, close_p, vol in updates:
            mock_time = timezone.make_aware(dt, timezone=ZoneInfo("UTC"))
            with patch("market.services.candles.timezone.now", return_value=mock_time):
                upsert_price_candle(
                    asset=asset,
                    interval_minutes=60,
                    open_price=Decimal(open_p),
                    high_price=Decimal(high_p),
                    low_price=Decimal(low_p),
                    close_price=Decimal(close_p),
                    volume=vol,
                )

        # Should have only 1 hourly candle
        hourly_candles = PriceCandle.objects.filter(asset=asset, interval_minutes=60)
        assert hourly_candles.count() == 1

        candle = hourly_candles.first()
        assert candle is not None
        # Open from first update
        assert candle.open_price == Decimal("100.00")
        # High is max across all updates
        assert candle.high_price == Decimal("103.00")
        # Low is min across all updates
        assert candle.low_price == Decimal("98.00")
        # Close from last update
        assert candle.close_price == Decimal("99.00")
        # Volume is sum of all
        assert candle.volume == 3000

    def test_60min_candles_aggregate_into_daily_candle(self, db):
        """
        Test that multiple hourly updates within the same day
        aggregate correctly into a single daily candle.
        """
        asset: Asset = AssetFactory()

        # Simulate updates across different hours of the same day
        updates = [
            (datetime.datetime(2025, 11, 14, 9, 30), "100.00", "102.00", "99.00", "101.00", 5000),
            (datetime.datetime(2025, 11, 14, 11, 15), "101.00", "105.00", "100.50", "104.00", 6000),
            (datetime.datetime(2025, 11, 14, 14, 45), "104.00", "104.50", "97.00", "98.00", 7000),
        ]

        for dt, open_p, high_p, low_p, close_p, vol in updates:
            mock_time = timezone.make_aware(dt, timezone=ZoneInfo("UTC"))
            with patch("market.services.candles.timezone.now", return_value=mock_time):
                upsert_price_candle(
                    asset=asset,
                    interval_minutes=1440,
                    open_price=Decimal(open_p),
                    high_price=Decimal(high_p),
                    low_price=Decimal(low_p),
                    close_price=Decimal(close_p),
                    volume=vol,
                )

        # Should have only 1 daily candle
        daily_candles = PriceCandle.objects.filter(asset=asset, interval_minutes=1440)
        assert daily_candles.count() == 1

        candle = daily_candles.first()
        assert candle is not None
        # Open from first update
        assert candle.open_price == Decimal("100.00")
        # High is max across all updates
        assert candle.high_price == Decimal("105.00")
        # Low is min across all updates
        assert candle.low_price == Decimal("97.00")
        # Close from last update
        assert candle.close_price == Decimal("98.00")
        # Volume is sum of all
        assert candle.volume == 18000

    def test_next_day_creates_new_daily_candle(self, db):
        """
        Test that updates on different days create separate daily candles.
        """
        asset: Asset = AssetFactory()

        # Day 1
        day1_time = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 0),
            timezone=ZoneInfo("UTC"),
        )
        with patch("market.services.candles.timezone.now", return_value=day1_time):
            upsert_price_candle(
                asset=asset,
                interval_minutes=1440,
                open_price=Decimal("100.00"),
                high_price=Decimal("102.00"),
                low_price=Decimal("99.00"),
                close_price=Decimal("101.00"),
                volume=5000,
            )

        # Day 2
        day2_time = timezone.make_aware(
            datetime.datetime(2025, 11, 15, 10, 0),
            timezone=ZoneInfo("UTC"),
        )
        with patch("market.services.candles.timezone.now", return_value=day2_time):
            upsert_price_candle(
                asset=asset,
                interval_minutes=1440,
                open_price=Decimal("101.00"),
                high_price=Decimal("103.00"),
                low_price=Decimal("100.00"),
                close_price=Decimal("102.00"),
                volume=6000,
            )

        # Should have 2 daily candles
        daily_candles = PriceCandle.objects.filter(asset=asset, interval_minutes=1440)
        assert daily_candles.count() == 2


class TestCandleTimezoneHandling:
    """Tests for timezone handling in candle bucketing."""

    def test_candle_bucket_respects_exchange_timezone(self, db):
        """
        Test that candle buckets are calculated based on the exchange's timezone.
        """
        # Create exchange in New York timezone
        exchange = ExchangeFactory(
            timezone="America/New_York",
            open_time=datetime.time(9, 30),
            close_time=datetime.time(16, 0),
        )
        asset: Asset = AssetFactory(exchange=exchange)

        # 10:02 AM in New York = 15:02 UTC (during EST, Nov 14 2025)
        # This should bucket to 10:00 AM New York time
        mock_time = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 15, 2),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=mock_time):
            candle = upsert_price_candle(
                asset=asset,
                interval_minutes=5,
                open_price=Decimal("100.00"),
                high_price=Decimal("101.00"),
                low_price=Decimal("99.00"),
                close_price=Decimal("100.50"),
                volume=1000,
            )

        # The bucket start should be 10:00 AM New York = 15:00 UTC
        expected_start = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 15, 0),
            timezone=ZoneInfo("UTC"),
        )
        assert candle.start_at == expected_start

    def test_daily_candle_uses_exchange_midnight(self, db):
        """
        Test that daily candles start at midnight in the exchange's timezone.
        """
        # Create exchange in Tokyo timezone
        exchange = ExchangeFactory(
            timezone="Asia/Tokyo",
            open_time=datetime.time(9, 0),
            close_time=datetime.time(15, 0),
        )
        asset: Asset = AssetFactory(exchange=exchange)

        # 10:00 AM Tokyo = 01:00 UTC (JST is UTC+9)
        mock_time = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 1, 0),
            timezone=ZoneInfo("UTC"),
        )

        with patch("market.services.candles.timezone.now", return_value=mock_time):
            candle = upsert_price_candle(
                asset=asset,
                interval_minutes=1440,
                open_price=Decimal("100.00"),
                high_price=Decimal("101.00"),
                low_price=Decimal("99.00"),
                close_price=Decimal("100.50"),
                volume=1000,
            )

        # Daily candle should start at midnight Tokyo = 15:00 UTC previous day
        expected_start = timezone.make_aware(
            datetime.datetime(2025, 11, 13, 15, 0),
            timezone=ZoneInfo("UTC"),
        )
        assert candle.start_at == expected_start
