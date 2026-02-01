# mypy: disable-error-code=assignment
# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

from decimal import Decimal
from market.services import update_stock_prices_simulation
from market.models import Asset, PriceCandle
from market.tests.factories import StockFactory, PriceCandleFactory


class TestSimulatedMarket:

    def test_update_stock_prices_with_existing_price(self, db):
        """
        Test that stock prices are updated based on the last known price.
        """
        stock: Asset = StockFactory()
        initial_price = Decimal('100.00')
        PriceCandleFactory(asset=stock, open_price=initial_price, close_price=initial_price)

        update_stock_prices_simulation([stock])

        assert PriceCandle.objects.filter(asset=stock, interval_minutes=5).count() >= 1
        
        latest_price_entry = PriceCandle.objects.filter(asset=stock, interval_minutes=5).latest('start_at')
        assert latest_price_entry.close_price != initial_price
        assert latest_price_entry.source == 'SIMULATION'

    def test_update_stock_prices_with_no_prior_price(self, db):
        """
        Test that a new random price is generated if no history exists.
        """
        stock: Asset = StockFactory()

        update_stock_prices_simulation([stock])

        assert PriceCandle.objects.filter(asset=stock, interval_minutes=5).count() >= 1
        
        latest_price_entry = PriceCandle.objects.filter(asset=stock, interval_minutes=5).latest('start_at')
        assert latest_price_entry.close_price > 0
        assert 50.0 <= latest_price_entry.close_price <= 250.0

    def test_update_multiple_stock_prices(self, db):
        """
        Test that multiple stocks are updated correctly in one go.
        """
        stock1: Asset = StockFactory()
        stock2: Asset = StockFactory()
        PriceCandleFactory(asset=stock1, open_price=Decimal('150.00'), close_price=Decimal('150.00'))
        PriceCandleFactory(asset=stock2, open_price=Decimal('200.00'), close_price=Decimal('200.00'))

        update_stock_prices_simulation([stock1, stock2])

        assert PriceCandle.objects.filter(asset=stock1, interval_minutes=5).count() >= 1
        assert PriceCandle.objects.filter(asset=stock2, interval_minutes=5).count() >= 1

        latest_price1 = stock1.get_latest_price()
        latest_price2 = stock2.get_latest_price()

        assert latest_price1 != Decimal('150.00')
        assert latest_price2 != Decimal('200.00')

    def test_no_stocks_to_update(self, db):
        """
        Test that the simulation handles an empty list of stocks gracefully.
        """
        update_stock_prices_simulation([])

        assert PriceCandle.objects.count() == 0
