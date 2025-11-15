from config.celery import app as celery_app
from django.conf import settings
from celery import shared_task
import logging

from apps.market.models import CurrencyAsset, Stock, Exchange

from .simulation import SimulatedMarket
logger = logging.getLogger(__name__)

@shared_task
def update_market_data():
    """
    Selectively updates prices based on whether the asset's exchange is open.
    """
    # 1. First do stock assets
    open_exchanges = [ex for ex in Exchange.objects.all() if ex.is_currently_open()]
    
    stocks_to_update = Stock.objects.filter(is_active=True, exchange__in=open_exchanges)

    if not stocks_to_update.exists():
        logger.info("No active stocks found for currently open exchanges. Skipping update.")
    
    # 2. Second, do currency assets

    currency_assets_to_update = CurrencyAsset.objects.filter(is_active=True)

    if not currency_assets_to_update.exists():
        logger.info("No active currency assets found. Skipping update.")
    
    #TODO: Check not weekends/holidays for currency assets

    if settings.MARKET_DATA_MODE == 'SIMULATION':
        # update stocks
        SimulatedMarket.update_stock_prices(stocks_to_update)


        # update currency assets


        pass
    elif settings.MARKET_DATA_MODE == 'LIVE':
        # update stocks


        # update currency assets

        
        pass

    return f"Updated prices for {len(stocks_to_update)} stocks."