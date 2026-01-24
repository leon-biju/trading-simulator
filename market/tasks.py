from celery import shared_task
import logging

from market.models import CurrencyAsset, Stock, Exchange
from config.constants import MARKET_DATA_MODE

from .services import update_stock_prices_simulation, update_currency_prices
from .api_access import get_currency_layer_api_data

@shared_task # type: ignore[untyped-decorator]
def update_stock_data() -> str:
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
    else:
        # update stocks
        return "Live stock price update not implemented yet."

@shared_task # type: ignore[untyped-decorator]
def update_currency_data() -> dict[str, int] | str:
    """
    Updates currency asset prices. Always Live
    """
    currencies = CurrencyAsset.objects.filter(is_active=True)

    if not currencies.exists():
        return "No active currencies found. Skipping update."
    
    json_data = get_currency_layer_api_data()

    if json_data is None:
        return "Currency data fetch failed."
    
    count = update_currency_prices(json_data)

    return {"rows_inserted": count}

