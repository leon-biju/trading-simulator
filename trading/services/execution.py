"""
Order execution logic.

Handles the actual execution of orders including buy/sell execution,
price condition checking, and market availability checks.
"""
from decimal import Decimal
from typing import Optional

from django.db import transaction

from trading.models import Order, OrderSide, OrderStatus, OrderType, Position, Trade
from market.models import Asset
from wallets.models import Wallet, Transaction

from trading.services.utils import round_to_two_dp, round_to_eight_dp

from config.constants import TRADING_FEE_PERCENTAGE


def _can_execute_immediately(asset: Asset) -> bool:
    """Check if an asset order can be executed immediately."""
    if not asset.is_active:
        return False
    if not asset.exchange.is_currently_open():
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


def execute_order(
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
    execution_price = order.asset.get_latest_price()
    if execution_price is None:
        raise LookupError(f"Price not available for {order.asset.ticker}")
    total_value = round_to_two_dp(order.quantity * execution_price)
    fee = round_to_two_dp(total_value * TRADING_FEE_PERCENTAGE)
    
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
        description=f"BUY {order.quantity} {order.asset.ticker} @ {execution_price} (fee: {fee})"
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
        description=f"SELL {order.quantity} {order.asset.ticker} @ {execution_price} (fee: {fee})"
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
            if not _can_execute_immediately(asset):
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
            
            return execute_order(order, wallet, position)
            
    except Order.DoesNotExist:
        raise LookupError("Order not found")
    except (Wallet.DoesNotExist, Position.DoesNotExist):
        # Resources missing - order should be rejected
        return None
