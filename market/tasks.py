from celery import shared_task
#import logging
import datetime
from django.utils import timezone

from market.models import Asset, Currency, Exchange, FXRate
from config.constants import MARKET_DATA_MODE

from .services.simulation import update_asset_prices_simulation
from .services.fx import update_currency_prices
from .api_access import get_currency_layer_api_data

@shared_task # type: ignore[untyped-decorator]
def update_asset_data() -> str:
    """
    Selectively updates prices based on whether the asset's exchange is open.
    """
    open_exchanges = [ex for ex in Exchange.objects.all() if ex.is_currently_open()]
    if not open_exchanges:
        return "No exchanges are currently open. Skipping update."
    
    assets_to_update = Asset.objects.filter(
        is_active=True,
        exchange__in=open_exchanges,
    )

    if not assets_to_update.exists():
        return "No active assets found for currently open exchanges. Skipping update."
    
    if MARKET_DATA_MODE == 'SIMULATION':
        # update assets
        update_asset_prices_simulation(assets_to_update)
        return f"Updated simulated prices for {len(assets_to_update)} assets."
    else:
        # update assets
        return "Live asset price update not implemented yet."

@shared_task # type: ignore[untyped-decorator]
def update_currency_data() -> dict[str, int] | str:
    """
    Updates currency asset prices. Always Live
    """
    currencies = Currency.objects.exclude(is_base=True)

    if not currencies.exists():
        return "No currencies found. Skipping update."
    
    # Check if data is fresh
    latest_fx_rate_timestamp = FXRate.objects.order_by("-last_updated").first()
    if latest_fx_rate_timestamp is not None:
        if (timezone.now() - latest_fx_rate_timestamp.last_updated) < datetime.timedelta(hours=24): #TODO: Make configurable
            return "Currency data is fresh. Skipping update."

    json_data = get_currency_layer_api_data()

    if json_data is None:
        return "Currency data fetch failed."

    count = update_currency_prices(json_data)

    return {"rows_inserted": count}



def aggregate_asset_prices() -> str:
    """
    Aggregates intraday asset prices into daily candles.
    """
    # Placeholder implementation
    return "Asset price aggregation not implemented yet."

