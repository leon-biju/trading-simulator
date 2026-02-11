import os
import logging
from celery import Celery
from celery.signals import worker_ready


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

    # Use app.send_task() to avoid importing tasks before Django apps are ready
    app.send_task('market.tasks.market_tick')
    app.send_task('market.tasks.update_currency_data')
    app.send_task('trading.tasks.expire_stale_orders')
    app.send_task('trading.tasks.snapshot_all_portfolios')

    logger.info("Startup tasks dispatched.")