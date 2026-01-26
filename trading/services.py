"""
Trading services module.

Handles order placement, execution, and cancellation following the service layer pattern.
All business logic for trading is encapsulated here.

Error Handling:
- ValueError: Validation errors (insufficient funds, invalid input, etc.)
- LookupError: Missing resources (wallet not found, asset not found, etc.)
- RuntimeError: Unexpected failures
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from django.db import transaction
from django.utils import timezone

from trading.models import Order, OrderSide, OrderStatus, OrderType, Position, Trade
from market.models import Asset, Stock
from wallets.models import Wallet, Transaction


# Fee percentage for trades (0.1%)
TRADING_FEE_PERCENTAGE = Decimal('0.001')


def round_to_two_dp(value: Decimal) -> Decimal:
    """Round decimal to 2 decimal places."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def round_to_eight_dp(value: Decimal) -> Decimal:
    """Round decimal to 8 decimal places (for quantities)."""
    return value.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)


def _get_execution_price(order: Order) -> Decimal:
    """
    Get the execution price for an order.
    For MARKET orders: use current market price.
    For LIMIT orders: use limit price (only called when price condition is met).
    
    Raises:
        LookupError: If price is not available
    """
    if order.order_type == OrderType.LIMIT:
        if order.limit_price is None:
            raise ValueError("LIMIT order missing limit_price")
        return order.limit_price
    
    # MARKET order - use current price
    current_price = order.asset.get_latest_price()
    if current_price is None:
        raise LookupError(f"Price not available for {order.asset.symbol}")
    return current_price


def _can_execute_immediately(stock: Stock) -> bool:
    """Check if a stock order can be executed immediately."""
    if not stock.is_active:
        return False
    if not stock.exchange.is_currently_open():
        return False
    return True


def _check_limit_price_condition(order: Order, current_price: Decimal) -> bool:
    """
    Check if limit price condition is met for execution.
    BUY LIMIT: Execute when market price <= limit price
    SELL LIMIT: Execute when market price >= limit price
    """
    if order.order_type != OrderType.LIMIT:
        return True  # MARKET orders always meet condition
    
    if order.limit_price is None:
        return False
    
    if order.side == OrderSide.BUY:
        return current_price <= order.limit_price
    else:  # SELL
        return current_price >= order.limit_price


def _calculate_order_cost(quantity: Decimal, price: Decimal) -> Decimal:
    """Calculate the cost of an order (quantity * price), rounded to 2dp."""
    return round_to_two_dp(quantity * price)


def _calculate_fee(total_value: Decimal) -> Decimal:
    """Calculate trading fee based on total value."""
    return round_to_two_dp(total_value * TRADING_FEE_PERCENTAGE)


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
            raise LookupError(f"Price not available for {asset.symbol}")
    
    assert reserve_price is not None  # Type narrowing
    reserved_amount = _calculate_order_cost(quantity, reserve_price)
    
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
            can_execute = False
            try:
                stock = Stock.objects.get(pk=asset.pk)
                can_execute = _can_execute_immediately(stock)
            except Stock.DoesNotExist:
                # Not a stock (e.g., currency) - can always trade if active
                can_execute = asset.is_active
            
            if can_execute:
                # For LIMIT orders, check price condition
                current_price = asset.get_latest_price()
                if current_price is not None and _check_limit_price_condition(order, current_price):
                    _execute_order(order, wallet)
            
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
                raise ValueError(f"Insufficient holdings of {asset.symbol}")
            
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
            can_execute = False
            try:
                stock = Stock.objects.get(pk=asset.pk)
                can_execute = _can_execute_immediately(stock)
            except Stock.DoesNotExist:
                # Not a stock (e.g., currency) - can always trade if active
                can_execute = asset.is_active
            
            if can_execute:
                # For LIMIT orders, check price condition
                current_price = asset.get_latest_price()
                if current_price is not None and _check_limit_price_condition(order, current_price):
                    _execute_order(order, wallet, position)
            
            return order
            
    except Position.DoesNotExist:
        raise LookupError(f"No position found for {asset.symbol}")
    except Wallet.DoesNotExist:
        raise LookupError(f"Wallet not found for currency {asset.currency.code}")


def _execute_order(
    order: Order,
    wallet: Wallet,
    position: Optional[Position] = None,
) -> Trade:
    """
    Execute a pending order at market price.
    
    This function expects to be called within an atomic transaction
    with the wallet (and position for SELL) already locked via select_for_update.
    
    Args:
        order: The order to execute
        wallet: The user's wallet (must be locked)
        position: The user's position (must be locked for SELL orders)
        
    Returns:
        Trade: The created trade record
        
    Raises:
        ValueError: Insufficient funds at execution time
        LookupError: Price not available
    """
    if order.status != OrderStatus.PENDING:
        raise ValueError(f"Cannot execute order with status {order.status}")
    
    # Get execution price
    execution_price = _get_execution_price(order)
    total_value = _calculate_order_cost(order.quantity, execution_price)
    fee = _calculate_fee(total_value)
    
    if order.side == OrderSide.BUY:
        return _execute_buy_order(order, wallet, execution_price, total_value, fee)
    else:
        if position is None:
            # Fetch and lock position if not provided
            position = Position.objects.select_for_update().get(
                user_id=order.user_id,
                asset=order.asset
            )
        return _execute_sell_order(order, wallet, position, execution_price, total_value, fee)


def _execute_buy_order(
    order: Order,
    wallet: Wallet,
    execution_price: Decimal,
    total_value: Decimal,
    fee: Decimal,
) -> Trade:
    """Execute a BUY order."""
    total_cost = total_value + fee
    
    # Release the reserved amount from pending
    wallet.pending_balance -= order.reserved_amount
    
    # Check if we have enough balance (price may have changed for MARKET orders)
    if wallet.balance < total_cost:
        # Insufficient funds - reject order
        order.status = OrderStatus.REJECTED
        order.save(update_fields=['status', 'updated_at'])
        wallet.save(update_fields=['pending_balance', 'updated_at'])
        raise ValueError(f"Insufficient funds at execution: need {total_cost}, have {wallet.balance}")
    
    # Deduct from actual balance
    wallet.balance -= total_cost
    wallet.save(update_fields=['balance', 'pending_balance', 'updated_at'])
    
    # Create wallet transaction
    tx = Transaction.objects.create(
        wallet=wallet,
        amount=-total_cost,
        balance_after=wallet.balance,
        source=Transaction.Source.BUY,
        description=f"BUY {order.quantity} {order.asset.symbol} @ {execution_price} (fee: {fee})"
    )
    
    # Update or create position
    position, created = Position.objects.get_or_create(
        user_id=order.user_id,
        asset=order.asset,
        defaults={
            'quantity': Decimal('0'),
            'pending_quantity': Decimal('0'),
            'average_cost': Decimal('0'),
        }
    )
    
    if not created:
        # Lock existing position
        position = Position.objects.select_for_update().get(pk=position.pk)
    
    # Update position with weighted average cost
    if position.quantity == 0:
        position.average_cost = execution_price
    else:
        # Weighted average: (old_qty * old_avg + new_qty * new_price) / total_qty
        total_qty = position.quantity + order.quantity
        position.average_cost = round_to_eight_dp(
            (position.quantity * position.average_cost + order.quantity * execution_price) / total_qty
        )
    
    position.quantity += order.quantity
    position.save(update_fields=['quantity', 'average_cost', 'updated_at'])
    
    # Update order status
    order.status = OrderStatus.FILLED
    order.reserved_amount = Decimal('0')
    order.save(update_fields=['status', 'reserved_amount', 'updated_at'])
    
    # Create trade record
    trade = Trade.objects.create(
        order=order,
        user_id=order.user_id,
        asset=order.asset,
        side=OrderSide.BUY,
        quantity=order.quantity,
        price=execution_price,
        fee=fee,
        fee_currency=order.asset.currency,
        wallet_transaction=tx,
    )
    
    return trade


def _execute_sell_order(
    order: Order,
    wallet: Wallet,
    position: Position,
    execution_price: Decimal,
    total_value: Decimal,
    fee: Decimal,
) -> Trade:
    """Execute a SELL order."""
    net_proceeds = total_value - fee
    
    # Release reserved shares
    position.pending_quantity -= order.quantity
    
    # Calculate realized P&L
    realized_pnl = (execution_price - position.average_cost) * order.quantity - fee
    
    # Update position
    position.quantity -= order.quantity
    position.realized_pnl += realized_pnl
    position.save(update_fields=['quantity', 'pending_quantity', 'realized_pnl', 'updated_at'])
    
    # Credit wallet
    wallet.balance += net_proceeds
    wallet.save(update_fields=['balance', 'updated_at'])
    
    # Create wallet transaction
    tx = Transaction.objects.create(
        wallet=wallet,
        amount=net_proceeds,
        balance_after=wallet.balance,
        source=Transaction.Source.SELL,
        description=f"SELL {order.quantity} {order.asset.symbol} @ {execution_price} (fee: {fee})"
    )
    
    # Update order status
    order.status = OrderStatus.FILLED
    order.save(update_fields=['status', 'updated_at'])
    
    # Create trade record
    trade = Trade.objects.create(
        order=order,
        user_id=order.user_id,
        asset=order.asset,
        side=OrderSide.SELL,
        quantity=order.quantity,
        price=execution_price,
        fee=fee,
        fee_currency=order.asset.currency,
        wallet_transaction=tx,
    )
    
    return trade


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
            
            if order.status != OrderStatus.PENDING:
                raise ValueError(f"Cannot cancel order with status {order.status}")
            
            if order.side == OrderSide.BUY:
                # Release reserved funds
                wallet = Wallet.objects.select_for_update().get(
                    user_id=user_id,
                    currency=order.asset.currency
                )
                wallet.pending_balance -= order.reserved_amount
                wallet.save(update_fields=['pending_balance', 'updated_at'])
            else:
                # Release reserved shares
                position = Position.objects.select_for_update().get(
                    user_id=user_id,
                    asset=order.asset
                )
                position.pending_quantity -= order.quantity
                position.save(update_fields=['pending_quantity', 'updated_at'])
            
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = timezone.now()
            order.reserved_amount = Decimal('0')
            order.save(update_fields=['status', 'cancelled_at', 'reserved_amount', 'updated_at'])
            
            return order
            
    except Order.DoesNotExist:
        raise LookupError("Order not found")
    except (Wallet.DoesNotExist, Position.DoesNotExist) as e:
        raise RuntimeError(f"Failed to release reservation: {str(e)}")


def execute_pending_order(order_id: int) -> Optional[Trade]:
    """
    Attempt to execute a pending order.
    
    Called by Celery task when market opens or price conditions change.
    
    Args:
        order_id: The order to execute
        
    Returns:
        Trade if executed, None if conditions not met
        
    Raises:
        LookupError: Order not found
        ValueError: Order cannot be executed
    """
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            
            if order.status != OrderStatus.PENDING:
                return None
            
            # Check if market is open for stocks
            asset = order.asset
            try:
                stock = Stock.objects.get(pk=asset.pk)
                if not _can_execute_immediately(stock):
                    return None
            except Stock.DoesNotExist:
                # Not a stock - check if asset is active
                if not asset.is_active:
                    return None
            
            # Check price conditions for LIMIT orders
            current_price = asset.get_latest_price()
            if current_price is None:
                return None
            
            if not _check_limit_price_condition(order, current_price):
                return None
            
            # Lock wallet
            wallet = Wallet.objects.select_for_update().get(
                user_id=order.user_id,
                currency=asset.currency
            )
            
            # Lock position for SELL orders
            position = None
            if order.side == OrderSide.SELL:
                position = Position.objects.select_for_update().get(
                    user_id=order.user_id,
                    asset=asset
                )
            
            return _execute_order(order, wallet, position)
            
    except Order.DoesNotExist:
        raise LookupError("Order not found")
    except (Wallet.DoesNotExist, Position.DoesNotExist):
        # Resources missing - order should be rejected
        return None


def get_pending_orders_for_exchange(exchange_code: str) -> list[Order]:
    """
    Get all pending orders for assets on a specific exchange.
    Used by Celery task when market opens.
    """
    return list(
        Order.objects.filter(
            status=OrderStatus.PENDING,
            asset__stock__exchange__code=exchange_code,
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


# =============================================================================
# Convenience functions matching the old API (for backward compatibility)
# =============================================================================

def place_stock_buy_order(
    user_id: int,
    stock: Stock,
    quantity: Decimal,
    order_type: OrderType,
    limit_price: Optional[Decimal] = None,
) -> Order:
    """
    Convenience function for placing stock buy orders.
    Wraps the generic place_order function.
    """
    return place_order(
        user_id=user_id,
        asset=stock,
        side=OrderSide.BUY,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price,
    )


def place_stock_sell_order(
    user_id: int,
    stock: Stock,
    quantity: Decimal,
    order_type: OrderType,
    limit_price: Optional[Decimal] = None,
) -> Order:
    """
    Convenience function for placing stock sell orders.
    Wraps the generic place_order function.
    """
    return place_order(
        user_id=user_id,
        asset=stock,
        side=OrderSide.SELL,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price,
    )