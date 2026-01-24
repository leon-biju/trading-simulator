# mypy: disable-error-code=assignment
# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

from decimal import Decimal
import pytest
from market.services import update_stock_prices_simulation
from market.models import PriceHistory, Stock
from market.tests.factories import StockFactory, PriceHistoryFactory


class TestSimulatedMarket:

    def test_update_stock_prices_with_existing_price(self, db):
        """
        Test that stock prices are updated based on the last known price.
        """
        stock: Stock = StockFactory()
        initial_price = Decimal('100.00')
        PriceHistoryFactory(asset=stock, price=initial_price)

        update_stock_prices_simulation([stock])

        assert PriceHistory.objects.filter(asset=stock).count() == 2
        
        latest_price_entry = PriceHistory.objects.filter(asset=stock).latest('timestamp')
        assert latest_price_entry.price != initial_price
        assert latest_price_entry.source == 'SIMULATION'

    def test_update_stock_prices_with_no_prior_price(self, db):
        """
        Test that a new random price is generated if no history exists.
        """
        stock: Stock = StockFactory()

        update_stock_prices_simulation([stock])

        assert PriceHistory.objects.filter(asset=stock).count() == 1
        
        latest_price_entry = PriceHistory.objects.get(asset=stock)
        assert latest_price_entry.price > 0
        assert 50.0 <= latest_price_entry.price <= 250.0

    def test_update_multiple_stock_prices(self, db):
        """
        Test that multiple stocks are updated correctly in one go.
        """
        stock1: Stock = StockFactory()
        stock2: Stock = StockFactory()
        PriceHistoryFactory(asset=stock1, price=Decimal('150.00'))
        PriceHistoryFactory(asset=stock2, price=Decimal('200.00'))

        update_stock_prices_simulation([stock1, stock2])

        assert PriceHistory.objects.filter(asset=stock1).count() == 2
        assert PriceHistory.objects.filter(asset=stock2).count() == 2

        latest_price1 = stock1.get_latest_price()
        latest_price2 = stock2.get_latest_price()

        assert latest_price1 != Decimal('150.00')
        assert latest_price2 != Decimal('200.00')

    def test_no_stocks_to_update(self, db):
        """
        Test that the simulation handles an empty list of stocks gracefully.
        """
        update_stock_prices_simulation([])

        assert PriceHistory.objects.count() == 0
