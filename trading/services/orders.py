"""
Order placement and cancellation logic.

Handles creating new orders (buy/sell) and cancelling existing orders.
"""
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from trading.models import Order, OrderSide, OrderStatus, OrderType, Position
from market.models import Asset
from wallets.models import Wallet

from trading.services.utils import round_to_two_dp
from trading.services.execution import (
    _can_execute_immediately,
    _check_limit_price_condition,
    execute_order,
)


def place_order(
    user_id: int,
    asset: Asset,
    side: OrderSide,
    quantity: Decimal,
    order_type: OrderType,
    limit_price: Optional[Decimal] = None,
) -> Order:
    """
    Place a new order for buying or selling an asset.
    
    For BUY orders: Validates available balance and reserves funds.
    For SELL orders: Validates available holdings and reserves shares.
    
    If market is open and conditions are met, executes immediately.
    Otherwise, creates a PENDING order.
    
    Args:
        user_id: The user placing the order
        asset: The asset to trade
        side: BUY or SELL
        quantity: Amount to trade
        order_type: MARKET or LIMIT
        limit_price: Required for LIMIT orders
        
    Returns:
        Order: The created order (may be PENDING or FILLED)
        
    Raises:
        ValueError: Validation errors (insufficient funds/holdings, invalid params)
        LookupError: Missing wallet, position, or price data
        RuntimeError: Unexpected failures
    """
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    
    if order_type == OrderType.LIMIT and limit_price is None:
        raise ValueError("Limit price is required for LIMIT orders")
    
    if order_type == OrderType.LIMIT and limit_price is not None and limit_price <= 0:
        raise ValueError("Limit price must be positive")
    
    if side == OrderSide.BUY:
        return _place_buy_order(user_id, asset, quantity, order_type, limit_price)
    else:
        return _place_sell_order(user_id, asset, quantity, order_type, limit_price)


def _place_buy_order(
    user_id: int,
    asset: Asset,
    quantity: Decimal,
    order_type: OrderType,
    limit_price: Optional[Decimal],
) -> Order:
    """
    Place a BUY order with proper fund reservation.
    
    Raises:
        ValueError: Insufficient funds or validation errors
        LookupError: Wallet or price not found
    """
    # Determine the price to use for reservation
    if order_type == OrderType.LIMIT:
        reserve_price = limit_price
    else:
        reserve_price = asset.get_latest_price()
        if reserve_price is None:
            raise LookupError(f"Price not available for {asset.ticker}")
    
    assert reserve_price is not None  # Type narrowing
    reserved_amount = round_to_two_dp(quantity * reserve_price)
    
    try:
        with transaction.atomic():
            # Lock wallet and check available balance
            wallet = Wallet.objects.select_for_update().get(
                user_id=user_id,
                currency=asset.currency
            )
            
            if wallet.available_balance < reserved_amount:
                raise ValueError(f"Insufficient funds in {asset.currency.code} wallet")
            
            # Reserve the funds
            wallet.pending_balance += reserved_amount
            wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            # Create the order
            order = Order.objects.create(
                user_id=user_id,
                asset=asset,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                reserved_amount=reserved_amount,
                status=OrderStatus.PENDING,
            )
            
            # Check if we can execute immediately
            can_execute = _can_execute_immediately(asset)
            
            if can_execute:
                # For LIMIT orders, check price condition
                current_price = asset.get_latest_price()
                if current_price is not None and _check_limit_price_condition(order, current_price):
                    execute_order(order, wallet)
            
            return order
            
    except Wallet.DoesNotExist:
        raise LookupError(f"Wallet not found for currency {asset.currency.code}")


def _place_sell_order(
    user_id: int,
    asset: Asset,
    quantity: Decimal,
    order_type: OrderType,
    limit_price: Optional[Decimal],
) -> Order:
    """
    Place a SELL order with proper share reservation.
    
    Raises:
        ValueError: Insufficient holdings or validation errors
        LookupError: Position or price not found
    """
    try:
        with transaction.atomic():
            # Lock position and check available quantity
            position = Position.objects.select_for_update().get(
                user_id=user_id,
                asset=asset
            )
            
            if position.available_quantity < quantity:
                raise ValueError(f"Insufficient holdings of {asset.ticker}")
            
            # Also lock the wallet for potential execution
            wallet = Wallet.objects.select_for_update().get(
                user_id=user_id,
                currency=asset.currency
            )
            
            # Reserve the shares
            position.pending_quantity += quantity
            position.save(update_fields=['pending_quantity', 'updated_at'])
            
            # Create the order
            order = Order.objects.create(
                user_id=user_id,
                asset=asset,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=order_type,
                limit_price=limit_price,
                reserved_amount=Decimal('0'),  # For SELL, we track via position.pending_quantity
                status=OrderStatus.PENDING,
            )
            
            # Check if we can execute immediately
            can_execute = _can_execute_immediately(asset)
            
            if can_execute:
                # For LIMIT orders, check price condition
                current_price = asset.get_latest_price()
                if current_price is not None and _check_limit_price_condition(order, current_price):
                    execute_order(order, wallet, position)
            
            return order
            
    except Position.DoesNotExist:
        raise LookupError(f"No position found for {asset.ticker}")
    except Wallet.DoesNotExist:
        raise LookupError(f"Wallet not found for currency {asset.currency.code}")


def cancel_order(order_id: int, user_id: int) -> Order:
    """
    Cancel a pending order and release reserved funds/shares.
    
    Args:
        order_id: The order to cancel
        user_id: The user cancelling (for verification)
        
    Returns:
        Order: The cancelled order
        
    Raises:
        ValueError: Order cannot be cancelled (already filled, etc.)
        LookupError: Order not found or doesn't belong to user
    """
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id, user_id=user_id)
            if order.status == OrderStatus.CANCELLED:
                raise ValueError("Order has already been cancelled")

            if order.status != OrderStatus.PENDING:
                raise ValueError(f"Cannot cancel order with status {order.status}")
            
            # Release wallet/position reservations
            release_order_reservation(order)
            
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = timezone.now()
            order.save(update_fields=['status', 'cancelled_at', 'reserved_amount', 'updated_at'])
            
            return order
            
    except Order.DoesNotExist:
        raise LookupError("Order not found")
    except (Wallet.DoesNotExist, Position.DoesNotExist) as e:
        raise RuntimeError(f"Failed to release reservation: {str(e)}")


def release_order_reservation(order: Order) -> None:
    """
    Release wallet or position reservations for a pending order.
    
    For BUY orders: releases pending_balance from the wallet.
    For SELL orders: releases pending_quantity from the position.
    Also resets the order's reserved_amount to zero.
    
    This function assumes it's called within a transaction.atomic() block
    and that the order is already locked with select_for_update().
    
    Args:
        order: The order whose reservations should be released.
               Must be locked via select_for_update().
    
    Raises:
        Wallet.DoesNotExist: If the wallet for the order doesn't exist
        Position.DoesNotExist: If the position for a SELL order doesn't exist
    """
    if order.side == OrderSide.BUY:
        # Release reserved funds
        wallet = Wallet.objects.select_for_update().get(
            user_id=order.user_id,
            currency=order.asset.currency
        )
        wallet.pending_balance -= order.reserved_amount
        wallet.save(update_fields=['pending_balance', 'updated_at'])
    else:
        # Release reserved shares
        position = Position.objects.select_for_update().get(
            user_id=order.user_id,
            asset=order.asset
        )
        position.pending_quantity -= order.quantity
        position.save(update_fields=['pending_quantity', 'updated_at'])
    
    # Reset the order's reserved amount
    order.reserved_amount = Decimal('0')

