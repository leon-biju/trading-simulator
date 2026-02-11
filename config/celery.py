import os
import logging
from celery import Celery
from celery.signals import worker_ready

from market.tasks import market_tick, update_currency_data
from trading.tasks import expire_stale_orders, snapshot_all_portfolios


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

logger = logging.getLogger(__name__)

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@worker_ready.connect  # type: ignore[untyped-decorator]
def on_startup(sender: object = None, **kwargs: object) -> None:
    """
    Runs once when the Celery worker boots.

    Catches up on anything that may have been missed while the system was down:
      - Asset price update (via the normal market_tick task)
      - FX rate refresh
      - Stale-order expiry
      - Portfolio snapshots (if last one is older than 24 h)
    """
    logger.info("Worker ready — running startup catch-up tasks.")

    market_tick.delay()
    update_currency_data.delay()
    expire_stale_orders.delay()
    snapshot_all_portfolios.delay()

    logger.info("Startup tasks dispatched.")