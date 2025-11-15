from decimal import Decimal
import pytest
from apps.market.simulation import SimulatedMarket
from apps.market.models import PriceHistory
from apps.market.tests.factories import StockFactory, PriceHistoryFactory

pytestmark = pytest.mark.django_db

class TestSimulatedMarket:

    def test_update_stock_prices_with_existing_price(self):
        """
        Test that stock prices are updated based on the last known price.
        """
        stock = StockFactory()
        initial_price = Decimal('100.00')
        PriceHistoryFactory(asset=stock, price=initial_price)

        simulator = SimulatedMarket()
        simulator.update_stock_prices([stock])

        assert PriceHistory.objects.filter(asset=stock).count() == 2
        
        latest_price_entry = PriceHistory.objects.filter(asset=stock).latest('timestamp')
        assert latest_price_entry.price != initial_price
        assert latest_price_entry.source == 'SIMULATION'

    def test_update_stock_prices_with_no_prior_price(self):
        """
        Test that a new random price is generated if no history exists.
        """
        stock = StockFactory()

        simulator = SimulatedMarket()
        simulator.update_stock_prices([stock])

        assert PriceHistory.objects.filter(asset=stock).count() == 1
        
        latest_price_entry = PriceHistory.objects.get(asset=stock)
        assert latest_price_entry.price > 0
        assert 50.0 <= latest_price_entry.price <= 250.0

    def test_update_multiple_stock_prices(self):
        """
        Test that multiple stocks are updated correctly in one go.
        """
        stock1 = StockFactory()
        stock2 = StockFactory()
        PriceHistoryFactory(asset=stock1, price=Decimal('150.00'))
        PriceHistoryFactory(asset=stock2, price=Decimal('200.00'))

        simulator = SimulatedMarket()
        simulator.update_stock_prices([stock1, stock2])

        assert PriceHistory.objects.filter(asset=stock1).count() == 2
        assert PriceHistory.objects.filter(asset=stock2).count() == 2

        latest_price1 = stock1.get_latest_price()
        latest_price2 = stock2.get_latest_price()

        assert latest_price1 != Decimal('150.00')
        assert latest_price2 != Decimal('200.00')

    def test_no_stocks_to_update(self):
        """
        Test that the simulation handles an empty list of stocks gracefully.
        """
        simulator = SimulatedMarket()
        simulator.update_stock_prices([])

        assert PriceHistory.objects.count() == 0
