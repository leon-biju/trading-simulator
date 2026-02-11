from celery import shared_task
import logging
import datetime
from django.utils import timezone

from market.models import Asset, Currency, Exchange, FXRate
from config.constants import MARKET_DATA_MODE

from .services.simulation import update_asset_prices_simulation
from .services.fx import update_currency_prices
from .api_access import get_currency_layer_api_data

from trading.tasks import check_limit_orders_for_assets, process_pending_orders_for_exchange



logger = logging.getLogger(__name__)


@shared_task # type: ignore[untyped-decorator]
def market_tick() -> str:
    """
    Main market heartbeat. Updates prices for assets on open exchanges,
    then chains downstream tasks:
      - check_limit_orders_for_assets  (for assets whose prices just changed)
      - process_pending_orders_for_exchange  (for each open exchange)
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
        update_asset_prices_simulation(assets_to_update)
    else:
        # TODO: Live asset price update not implemented yet.
        return "Live asset price update not implemented yet."

    # Now run downstream tasks for orders affected by these price changes
    asset_ids = list(assets_to_update.values_list("id", flat=True))
    check_limit_orders_for_assets.delay(asset_ids)

    for exchange in open_exchanges:
        process_pending_orders_for_exchange.delay(exchange.code)

    logger.info(f"Updated prices for {len(asset_ids)} assets on {len(open_exchanges)} exchanges.")
    return f"Updated simulated prices for {len(asset_ids)} assets across {len(open_exchanges)} exchanges."

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
