"""
Query functions for retrieving trading data.

Read-only operations for fetching orders, positions, and related data.
"""
from trading.models import Order, OrderStatus, Position


def get_pending_orders_for_exchange(exchange_code: str) -> list[Order]:
    """
    Get all pending orders for assets on a specific exchange.
    Used by Celery task when market opens.
    """
    return list(
        Order.objects.filter(
            status=OrderStatus.PENDING,
            asset__exchange__code=exchange_code,
        ).select_related('asset', 'user').order_by('created_at')
    )


def get_user_pending_orders(user_id: int, limit: int = 10) -> list[Order]:
    """Get pending orders for a user, ordered by creation time."""
    return list(
        Order.objects.filter(
            user_id=user_id,
            status=OrderStatus.PENDING,
        ).select_related('asset').order_by('-created_at')[:limit]
    )


def get_user_positions(user_id: int) -> list[Position]:
    """Get all open positions for a user."""
    return list(
        Position.objects.filter(
            user_id=user_id,
            quantity__gt=0,
        ).select_related('asset')
    )
