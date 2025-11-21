from celery import shared_task
import logging

from apps.market.models import CurrencyAsset, Stock, Exchange
from config.constants import MARKET_DATA_MODE

from .simulated_data import update_stock_prices_simulation, update_currency_prices_simulation
logger = logging.getLogger(__name__)

@shared_task
def update_stock_data():
    """
    Selectively updates prices based on whether the stock's exchange is open.
    """
    open_exchanges = [ex for ex in Exchange.objects.all() if ex.is_currently_open()]
    if not open_exchanges:
        return "No exchanges are currently open. Skipping update."
    
    stocks_to_update = Stock.objects.filter(is_active=True, exchange__in=open_exchanges)

    if not stocks_to_update.exists():
        return "No active stocks found for currently open exchanges. Skipping update."
    
    if MARKET_DATA_MODE == 'SIMULATION':
        # update stocks
        update_stock_prices_simulation(stocks_to_update)
        return f"Updated simulated prices for {len(stocks_to_update)} stocks."
    elif MARKET_DATA_MODE == 'LIVE':
        # update stocks
        return "Live stock price update not implemented yet."

    
