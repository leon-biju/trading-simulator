"""
Trading Celery tasks.

Handles scheduled order processing, particularly for pending orders when markets open.
"""
from celery import shared_task
import logging

from market.models import Exchange
from trading.models import Order, OrderStatus, OrderType

from trading.services.execution import execute_pending_order
from trading.services.queries import get_pending_orders_for_exchange
from trading.services.portfolio import snapshot_all_user_portfolios




logger = logging.getLogger(__name__)


@shared_task  # type: ignore[untyped-decorator]
def process_pending_orders_for_exchange(exchange_code: str) -> dict[str, int]:
    """
    Process all pending orders for a specific exchange.
    
    Called when an exchange opens. Iterates through pending orders in FIFO order
    and attempts to execute each one.
    
    Args:
        exchange_code: The exchange code (e.g., 'NYSE', 'NASDAQ')
        
    Returns:
        dict with counts of executed, failed, and skipped orders
    """
    
    results = {
        'executed': 0,
        'failed': 0,
        'skipped': 0,
    }
    
    pending_orders = get_pending_orders_for_exchange(exchange_code)
    logger.info(f"Processing {len(pending_orders)} pending orders for exchange {exchange_code}")
    
    for order in pending_orders:
        try:
            trade = execute_pending_order(order.id)
            if trade is not None:
                results['executed'] += 1
                logger.info(f"Executed order {order.id}: {order}")
            else:
                results['skipped'] += 1
                logger.debug(f"Skipped order {order.id}: conditions not met")
        except Exception as e:
            results['failed'] += 1
            logger.error(f"Failed to execute order {order.id}: {str(e)}")
    
    logger.info(f"Finished processing orders for {exchange_code}: {results}")
    return results


@shared_task  # type: ignore[untyped-decorator]
def schedule_market_open_tasks() -> str:
    """
    Scheduled task to check which exchanges are about to open and queue processing tasks.
    
    This should be run periodically (e.g., every minute) to check for markets
    that are transitioning from closed to open.
    
    TODO: Implement proper scheduling based on exchange open times.
    For now, this is a placeholder that can be called manually.
    """
    exchanges = Exchange.objects.all()
    queued = []
    
    for exchange in exchanges:
        if exchange.is_currently_open():
            # Queue the order processing task
            process_pending_orders_for_exchange.delay(exchange.code)
            queued.append(exchange.code)
    
    if queued:
        return f"Queued order processing for exchanges: {', '.join(queued)}"
    return "No exchanges currently open"


@shared_task  # type: ignore[untyped-decorator]
def check_limit_orders() -> dict[str, int]:
    """
    Check all pending LIMIT orders to see if their price conditions are now met.
    
    This can be called after price updates to check if any limit orders
    should be executed.
    
    TODO: Optimize by only checking orders for assets whose prices changed.
    """
    
    results = {
        'checked': 0,
        'executed': 0,
        'failed': 0,
    }
    
    # Get all pending LIMIT orders
    limit_orders = Order.objects.filter(
        status=OrderStatus.PENDING,
        order_type=OrderType.LIMIT,
    ).order_by('created_at')
    
    for order in limit_orders:
        results['checked'] += 1
        try:
            trade = execute_pending_order(order.id)
            if trade is not None:
                results['executed'] += 1
                logger.info(f"Executed limit order {order.id}: {order}")
        except Exception as e:
            results['failed'] += 1
            logger.error(f"Failed to execute limit order {order.id}: {str(e)}")
    
    return results


@shared_task  # type: ignore[untyped-decorator]
def snapshot_all_portfolios() -> dict[str, int]:
    """
    Create daily portfolio snapshots for all users.
    
    This task should be scheduled to run once daily (e.g., end of day)
    to capture the portfolio value for historical tracking.
    
    Returns:
        dict with counts of successful and failed snapshots
    """    
    logger.info("Starting daily portfolio snapshot task")
    results = snapshot_all_user_portfolios()
    logger.info(f"Portfolio snapshot complete: {results}")
    
    return results