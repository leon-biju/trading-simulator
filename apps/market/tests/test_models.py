import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.market.tests.factories import (
    CurrencyFactory,
    ExchangeFactory,
    PriceHistoryFactory,
    StockFactory,
)


class TestExchangeModel:
    def test_exchange_creation(self, db):
        exchange = ExchangeFactory(
            name="New York Stock Exchange",
            code="NYSE",
            timezone="America/New_York",
            open_time=datetime.time(9, 30),
            close_time=datetime.time(16, 0),
        )
        assert exchange.name == "New York Stock Exchange"
        assert exchange.code == "NYSE"
        assert str(exchange) == "New York Stock Exchange (NYSE)"

    def test_is_currently_open_during_trading_hours(self, db):
        exchange = ExchangeFactory(
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
        exchange = ExchangeFactory(
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
        exchange = ExchangeFactory(
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
        exchange = ExchangeFactory(timezone="Invalid/Timezone")
        assert exchange.is_currently_open() is False


class TestCurrencyModel:
    def test_currency_creation(self, db):
        currency = CurrencyFactory(code="USD", name="United States Dollar")
        assert currency.code == "USD"
        assert str(currency) == "USD"

    def test_base_currency_uniqueness(self, db):
        c1 = CurrencyFactory(code="USD", is_base=True)
        c2 = CurrencyFactory(code="EUR", is_base=True)

        c1.refresh_from_db()
        c2.refresh_from_db()

        assert c1.is_base is False
        assert c2.is_base is True

    def test_changing_base_currency(self, db):
        c1 = CurrencyFactory(code="USD", is_base=True)
        c2 = CurrencyFactory(code="EUR", is_base=False)

        c2.is_base = True
        c2.save()

        c1.refresh_from_db()
        c2.refresh_from_db()

        assert c1.is_base is False
        assert c2.is_base is True


class TestAssetModels:
    def test_stock_creation(self, db):
        stock = StockFactory(
            symbol="AAPL", name="Apple Inc.", exchange__code="NASDAQ"
        )
        assert stock.asset_type == "STOCK"
        assert stock.symbol == "AAPL"
        assert str(stock) == "Apple Inc. (AAPL) on NASDAQ"

    def test_get_latest_price(self, db):
        stock = StockFactory()
        PriceHistoryFactory(asset=stock, price=150.00)
        PriceHistoryFactory(asset=stock, price=155.50)

        assert stock.get_latest_price() == 155.50

    def test_get_latest_price_no_history(self, db):
        stock = StockFactory()
        assert stock.get_latest_price() is None


class TestPriceHistoryModel:
    def test_price_history_creation(self, db):
        stock = StockFactory()
        price = PriceHistoryFactory(asset=stock, price=200.25)
        assert price.asset == stock
        assert price.price == 200.25
        assert price.source == "SIMULATION"

    def test_price_history_ordering(self, db):
        stock = StockFactory()
        p1 = PriceHistoryFactory(
            asset=stock,
            price=100,
            timestamp=timezone.now() - datetime.timedelta(days=1),
        )
        p2 = PriceHistoryFactory(asset=stock, price=102)

        prices = stock.price_history.all()
        assert prices[0] == p2
        assert prices[1] == p1

    def test_get_latest_by(self, db):
        stock = StockFactory()
        PriceHistoryFactory(
            asset=stock,
            price=100,
            timestamp=timezone.now() - datetime.timedelta(days=1),
        )
        latest_price = PriceHistoryFactory(asset=stock, price=102)

        assert stock.price_history.latest() == latest_price
