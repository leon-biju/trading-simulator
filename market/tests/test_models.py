# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call
# mypy: disable-error-code=assignment
from time import sleep
import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from market.tests.factories import (
    CurrencyFactory,
    ExchangeFactory,
    PriceCandleFactory,
    StockFactory,
)
from market.models import Exchange, Currency, CurrencyAsset, Stock, PriceCandle


class TestExchangeModel:
    def test_exchange_creation(self, db):
        exchange: Exchange = ExchangeFactory(
            name="New York Stock Exchange",
            code="NYSE",
            timezone="America/New_York",
            open_time=datetime.time(9, 30),
            close_time=datetime.time(16, 0),
        )
        assert str(exchange.name) == "New York Stock Exchange"
        assert str(exchange.code) == "NYSE"
        assert str(exchange) == "New York Stock Exchange (NYSE)"

    def test_is_currently_open_during_trading_hours(self, db):
        exchange: Exchange = ExchangeFactory(
            timezone="America/New_York",
            open_time=datetime.time(9, 30),
            close_time=datetime.time(16, 0),
        )
        # Friday, November 14, 2025 10:00 AM in New York
        mock_time = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 10, 0),
            timezone=ZoneInfo("America/New_York"),
        )
        with patch("django.utils.timezone.now", return_value=mock_time):
            assert exchange.is_currently_open() is True

    def test_is_currently_open_outside_trading_hours(self, db):
        exchange: Exchange = ExchangeFactory(
            timezone="America/New_York",
            open_time=datetime.time(9, 30),
            close_time=datetime.time(16, 0),
        )
        # Friday, November 14, 2025 17:00 PM in New York
        mock_time = timezone.make_aware(
            datetime.datetime(2025, 11, 14, 17, 0),
            timezone=ZoneInfo("America/New_York"),
        )
        with patch("django.utils.timezone.now", return_value=mock_time):
            assert exchange.is_currently_open() is False

    def test_is_currently_open_on_weekend(self, db):
        exchange: Exchange = ExchangeFactory(
            timezone="America/New_York",
            open_time=datetime.time(9, 30),
            close_time=datetime.time(16, 0),
        )
        # Saturday, November 15, 2025 10:00 AM in New York
        mock_time = timezone.make_aware(
            datetime.datetime(2025, 11, 15, 10, 0),
            timezone=ZoneInfo("America/New_York"),
        )
        with patch("django.utils.timezone.now", return_value=mock_time):
            assert exchange.is_currently_open() is False

    def test_is_currently_open_with_invalid_timezone(self, db):
        exchange: Exchange = ExchangeFactory(timezone="Invalid/Timezone")
        assert exchange.is_currently_open() is False


class TestCurrencyModel:
    def test_currency_creation(self, db):
        currency: Currency = CurrencyFactory(code="USD", name="United States Dollar")
        assert currency.code == "USD"
        assert str(currency) == "USD"

    def test_base_currency_uniqueness(self, db):
        c1: Currency = CurrencyFactory(code="USD", is_base=True)
        c2: Currency = CurrencyFactory(code="EUR", is_base=True)

        c1.refresh_from_db()
        c2.refresh_from_db()

        assert c1.is_base is False
        assert c2.is_base is True

    def test_changing_base_currency(self, db):
        c1: Currency = CurrencyFactory(code="USD", is_base=True)
        c2: Currency = CurrencyFactory(code="EUR", is_base=False)

        c2.is_base = True
        c2.save()

        c1.refresh_from_db()
        c2.refresh_from_db()

        assert c1.is_base is False
        assert c2.is_base is True


class TestAssetModels:
    def test_stock_creation(self, db):
        stock: Stock = StockFactory(
            symbol="AAPL", name="Apple Inc.", exchange__code="NASDAQ"
        )
        assert stock.name == "Apple Inc."
        assert stock.asset_type == "STOCK"
        assert stock.symbol == "AAPL"
        assert str(stock) == "Apple Inc. (AAPL) on NASDAQ"

    def test_get_latest_price(self, db):
        stock: Stock = StockFactory()
        t0 = timezone.now()
        PriceCandleFactory(asset=stock, interval_minutes=1440, close_price=150.00, start_at=t0 - datetime.timedelta(seconds=60))
        PriceCandleFactory(asset=stock, interval_minutes=1440, close_price=155.50, start_at=t0)

        assert stock.get_latest_price() == 155.50

    def test_get_latest_price_no_history(self, db):
        stock: Stock = StockFactory()
        assert stock.get_latest_price() is None


class TestPriceCandleModel:
    def test_price_candle_creation(self, db):
        stock: Stock = StockFactory()
        candle: PriceCandle = PriceCandleFactory(asset=stock, close_price=200.25)
        assert candle.asset == stock
        assert candle.close_price == 200.25
        assert candle.source == "SIMULATION"

    def test_price_candle_ordering(self, db):
        t0 = timezone.now()
        stock: Stock = StockFactory()
        p1: PriceCandle = PriceCandleFactory(
            asset=stock,
            start_at=t0 - datetime.timedelta(minutes=10),
        )
        p2: PriceCandle = PriceCandleFactory(asset=stock, start_at=t0)

        prices = stock.price_candles.all()
        assert prices[0] == p2 
        assert prices[1] == p1

    def test_get_latest_by(self, db):
        t0 = timezone.now()
        stock: Stock = StockFactory()
        PriceCandleFactory(
            asset=stock,
            start_at=t0 - datetime.timedelta(days=1),
        )
        latest_price: PriceCandle = PriceCandleFactory(asset=stock, start_at=t0)

        assert stock.price_candles.latest() == latest_price
