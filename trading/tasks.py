"""
Trading Celery tasks.

Handles scheduled order processing, limit order checks, portfolio snapshots,
and stale order expiry.

Note: These tasks are primarily chained from the market heartbeat
(market.tasks.update_asset_data), not individually scheduled in Beat,
except for daily housekeeping tasks (snapshots, expiry).
"""
from celery import shared_task
import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
import datetime

from market.models import Exchange
from trading.models import Order, OrderSide, OrderStatus, OrderType, Position
from wallets.models import Wallet

from trading.services.execution import execute_pending_order
from trading.services.queries import get_pending_orders_for_exchange
from trading.services.portfolio import snapshot_all_user_portfolios
from trading.services.orders import release_order_reservation

from config.constants import ORDER_EXPIRY_DAYS




logger = logging.getLogger(__name__)


@shared_task  # type: ignore[untyped-decorator]
def process_pending_orders_for_exchange(exchange_code: str) -> dict[str, int]:
    """
    Process all pending MARKET orders for a specific exchange.
    
    Chained from market_tick when an exchange is open.
    Iterates through pending orders in FIFO order and attempts to execute each one.
    
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
def check_limit_orders_for_assets(asset_ids: list[int]) -> dict[str, int]:
    """
    Check pending LIMIT orders for specific assets to see if they can be executed.
    
    Chained from market_tick after prices are refreshed,
    scoped to only the assets whose prices just changed.
    
    Args:
        asset_ids: List of asset IDs that were updated
        
    Returns:
        dict with counts of checked, executed, and failed orders
    """
    
    results = {
        'checked': 0,
        'executed': 0,
        'failed': 0,
    }
    
    # Get all pending LIMIT orders for the specified assets
    limit_orders = Order.objects.filter(
        status=OrderStatus.PENDING,
        order_type=OrderType.LIMIT,
        asset_id__in=asset_ids,
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
    
    Scheduled daily via Beat. Captures portfolio value for historical tracking.
    
    Returns:
        dict with counts of successful and failed snapshots
    """    
    logger.info("Starting daily portfolio snapshot task")
    results = snapshot_all_user_portfolios()
    logger.info(f"Portfolio snapshot complete: {results}")
    
    return results


@shared_task  # type: ignore[untyped-decorator]
def expire_stale_orders(max_age_days: int = ORDER_EXPIRY_DAYS) -> dict[str, int]:
    """
    Expire pending orders older than max_age_days, releasing reserved funds/shares.
    
    Scheduled daily via Beat. Iterates stale orders individually so that
    wallet pending_balance and position pending_quantity are correctly unwound,
    rather than doing a bulk status update.
    
    Args:
        max_age_days: Orders pending longer than this are expired.
        
    Returns:
        dict with counts of expired, failed, and remaining pending orders
    """
    cutoff_date = timezone.now() - datetime.timedelta(days=max_age_days)
    stale_orders = Order.objects.filter(
        status=OrderStatus.PENDING,
        created_at__lt=cutoff_date,
    ).select_related('asset', 'asset__currency').order_by('created_at')
    
    results: dict[str, int] = {
        'expired': 0,
        'failed': 0,
    }
    
    for order in stale_orders:
        try:
            with transaction.atomic():
                order_locked = Order.objects.select_for_update().get(pk=order.id)

                # Skip if no longer pending (raced with execution or manual cancel)
                if order_locked.status != OrderStatus.PENDING:
                    continue

                # Release wallet/position reservations
                release_order_reservation(order_locked)

                order_locked.status = OrderStatus.EXPIRED
                order_locked.save(update_fields=['status', 'reserved_amount', 'updated_at'])

            results['expired'] += 1
            logger.info(f"Expired stale order {order.id} (created {order.created_at})")

        except Exception as e:
            results['failed'] += 1
            logger.error(f"Failed to expire order {order.id}: {str(e)}")
    
    remaining = Order.objects.filter(status=OrderStatus.PENDING).count()
    logger.info(
        f"Stale-order sweep complete: {results['expired']} expired, "
        f"{results['failed']} failed, {remaining} still pending."
    )
    results['remaining_pending'] = remaining
    return results