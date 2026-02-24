"""
Query functions for retrieving trading data.

Read-only operations for fetching orders, positions, and related data.
"""
from django.db.models import QuerySet
from typing import Iterator
from trading.models import Order, OrderStatus, Position

def get_pending_orders_for_exchange(exchange_code: str, chunk_size: int = 50) -> Iterator[Order]:
    """
    Iterate over pending orders for assets on a specific exchange in chunks.
    Memory-efficient alternative to original using lists.
    """
    return Order.objects.filter(
        status=OrderStatus.PENDING,
        asset__exchange__code=exchange_code,
    ).select_related('asset', 'user').order_by('created_at').iterator(chunk_size=chunk_size)


def get_user_pending_orders(user_id: int, limit: int = 10) -> QuerySet[Order]:
    """Get pending orders for a user, ordered by creation time."""
    return Order.objects.filter(
            user_id=user_id,
            status=OrderStatus.PENDING,
        ).select_related('asset').order_by('-created_at')[:limit]


def get_user_positions(user_id: int, chunk_size: int = 50) -> Iterator[Position]:
    """
    Iterate over open positions for a user in chunks.
    Memory-efficient alternative to get_user_positions.
    """
    return Position.objects.filter(
        user_id=user_id,
        quantity__gt=0,
    ).select_related('asset').iterator(chunk_size=chunk_size)
