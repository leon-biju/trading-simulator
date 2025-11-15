from unittest.mock import patch, MagicMock
import pytest
from django.test import override_settings

from apps.market.tasks import update_market_data
from apps.market.models import Stock, Exchange
from apps.market.tests.factories import ExchangeFactory, StockFactory, PriceHistoryFactory

pytestmark = pytest.mark.django_db

class TestMarketTasks:

    @patch('apps.market.tasks.SimulatedMarket.update_stock_prices')
    def test_update_market_data_simulation_mode(self, mock_update_stock_prices):
        """
        Test that the task calls the simulation service when MARKET_DATA_MODE is 'SIMULATION'.
        """
        # An open exchange
        open_exchange = ExchangeFactory(code="OPEN")
        # A closed exchange
        closed_exchange = ExchangeFactory(code="CLOSED")

        # Mock is_currently_open to control which exchange is considered open
        with patch.object(Exchange, 'is_currently_open', side_effect=lambda: self.code == "OPEN"):
            stock1 = StockFactory(exchange=open_exchange, is_active=True)
            StockFactory(exchange=closed_exchange, is_active=True) # This one should be ignored
            StockFactory(exchange=open_exchange, is_active=False) # This one should be ignored

            with override_settings(MARKET_DATA_MODE='SIMULATION'):
                result = update_market_data.delay().get()

            # The simulation should be called only with the active stock from the open exchange
            mock_update_stock_prices.assert_called_once()
            
            # Check the stocks passed to the simulation
            call_args, _ = mock_update_stock_prices.call_args
            passed_stocks = call_args[0]
            assert len(passed_stocks) == 1
            assert stock1 in passed_stocks

            assert "Updated prices for 1 stocks" in result

    @patch('apps.market.tasks.SimulatedMarket.update_stock_prices')
    def test_update_market_data_no_open_exchanges(self, mock_update_stock_prices):
        """
        Test that the simulation is not called if no exchanges are open.
        """
        exchange = ExchangeFactory()
        StockFactory(exchange=exchange, is_active=True)

        with patch.object(Exchange, 'is_currently_open', return_value=False):
            with override_settings(MARKET_DATA_MODE='SIMULATION'):
                result = update_market_data.delay().get()

        mock_update_stock_prices.assert_not_called()
        assert "Updated prices for 0 stocks" in result

    @patch('apps.market.tasks.SimulatedMarket.update_stock_prices')
    def test_update_market_data_no_active_stocks(self, mock_update_stock_prices):
        """
        Test that the simulation is not called if there are no active stocks for open exchanges.
        """
        exchange = ExchangeFactory()
        StockFactory(exchange=exchange, is_active=False)

        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with override_settings(MARKET_DATA_MODE='SIMULATION'):
                result = update_market_data.delay().get()

        # The service method is called with an empty queryset, but doesn't create new prices
        mock_update_stock_prices.assert_called_once_with(Stock.objects.none())
        assert "Updated prices for 0 stocks" in result

    # You would add a similar test for 'LIVE' mode, patching the live data fetching service
    @patch('apps.market.tasks.SimulatedMarket.update_stock_prices') # Placeholder
    def test_update_market_data_live_mode_not_implemented(self, mock_live_data_fetcher):
        """
        Test that the task runs in 'LIVE' mode but does nothing yet.
        """
        exchange = ExchangeFactory()
        StockFactory(exchange=exchange, is_active=True)

        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with override_settings(MARKET_DATA_MODE='LIVE'):
                result = update_market_data.delay().get()

        mock_live_data_fetcher.assert_not_called()
        assert "Updated prices for 1 stocks" in result
