"""
Comprehensive tests for trading order execution.

Tests cover:
- BUY/SELL order placement and execution
- MARKET/LIMIT order types
- Pending order handling (market closed, inactive assets)
- Order cancellation
- Position updates (quantity, average cost, P&L)
- Wallet balance and pending balance management
- Error handling (insufficient funds/holdings)
"""
import pytest
from unittest.mock import patch
from typing import Any, Tuple
from decimal import Decimal

from django.db.models import QuerySet
from django.contrib.auth import get_user_model

from accounts.models import CustomUser
from market.models import Stock, Exchange, PriceHistory
from trading.models import Order, OrderSide, OrderType, OrderStatus, Position, Trade
from trading.services import (
    place_order,
    place_stock_buy_order,
    place_stock_sell_order,
    cancel_order,
    execute_pending_order,
    get_user_pending_orders,
    get_user_positions,
    TRADING_FEE_PERCENTAGE,
)
from wallets.models import Wallet, Transaction


@pytest.fixture
def user_with_wallets(market_data: dict[str, dict[str, Any]]) -> Tuple[CustomUser, QuerySet[Wallet]]:
    """Create a test user with wallets after market data is set up."""
    User = get_user_model()
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='StrongV3ryStrongPasswd!'
    )
    wallets = Wallet.objects.filter(user=user)
    
    # Add USD funds for stock trading (stocks are priced in USD)
    usd_wallet = wallets.get(currency__code='USD')
    usd_wallet.balance = Decimal('100000.00')
    usd_wallet.save()
    
    return user, wallets


@pytest.fixture
def user_with_position(
    user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
    market_data: dict[str, dict[str, Any]]
) -> Tuple[CustomUser, QuerySet[Wallet], Position]:
    """Create a user with an existing stock position."""
    user, wallets = user_with_wallets
    stock = market_data['stocks']['AAPL']
    
    # Create a position as if user had previously bought shares
    position = Position.objects.create(
        user=user,
        asset=stock,
        quantity=Decimal('100'),
        pending_quantity=Decimal('0'),
        average_cost=Decimal('140.00'),  # Bought at $140
    )
    
    return user, wallets, position


class TestBuyOrderPlacement:
    """Tests for BUY order placement."""
    
    @pytest.mark.django_db
    def test_market_buy_order_executes_when_market_open(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Market BUY order executes immediately when exchange is open."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.FILLED
        assert order.reserved_amount == Decimal('0')
        
        # Check position was created
        position = Position.objects.get(user=user, asset=stock)
        assert position.quantity == Decimal('10')
        assert position.average_cost == stock_price
        
        # Check wallet balance was deducted with fee
        usd_wallet.refresh_from_db()
        total_cost = (Decimal('10') * stock_price)
        fee = (total_cost * TRADING_FEE_PERCENTAGE).quantize(Decimal('0.01'))
        assert usd_wallet.balance == initial_balance - total_cost - fee
        assert usd_wallet.pending_balance == Decimal('0')
        
        # Check trade record was created
        trade = Trade.objects.get(order=order)
        assert trade.quantity == Decimal('10')
        assert trade.price == stock_price
        assert trade.fee == fee
        
        # Check wallet transaction was created
        tx = Transaction.objects.filter(wallet=usd_wallet, source=Transaction.Source.BUY).first()
        assert tx is not None
        assert tx.amount == -(total_cost + fee)
    
    @pytest.mark.django_db
    def test_market_buy_order_pending_when_market_closed(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Market BUY order becomes pending when exchange is closed."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Funds should be reserved
        expected_reserved = (Decimal('10') * stock_price).quantize(Decimal('0.01'))
        assert order.reserved_amount == expected_reserved
        
        usd_wallet.refresh_from_db()
        assert usd_wallet.balance == initial_balance  # Not deducted yet
        assert usd_wallet.pending_balance == expected_reserved
        assert usd_wallet.available_balance == initial_balance - expected_reserved
        
        # No position created yet
        assert not Position.objects.filter(user=user, asset=stock).exists()
        
        # No trade created
        assert not Trade.objects.filter(order=order).exists()
    
    @pytest.mark.django_db
    def test_limit_buy_order_executes_when_price_met(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """LIMIT BUY order executes when market price <= limit price."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        current_price = stock.get_latest_price()
        assert current_price is not None
        
        # Set limit price above current price (should execute)
        limit_price = current_price + Decimal('10')
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('5'),
                order_type=OrderType.LIMIT,
                limit_price=limit_price,
            )
        
        # Should execute at limit price since condition is met
        assert order.status == OrderStatus.FILLED
        
        trade = Trade.objects.get(order=order)
        assert trade.price == limit_price
    
    @pytest.mark.django_db
    def test_limit_buy_order_pending_when_price_not_met(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """LIMIT BUY order stays pending when market price > limit price."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        current_price = stock.get_latest_price()
        assert current_price is not None
        
        # Set limit price below current price (should not execute)
        limit_price = current_price - Decimal('20')
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('5'),
                order_type=OrderType.LIMIT,
                limit_price=limit_price,
            )
        
        assert order.status == OrderStatus.PENDING
        assert order.limit_price == limit_price
        
        # Funds reserved at limit price
        expected_reserved = (Decimal('5') * limit_price).quantize(Decimal('0.01'))
        assert order.reserved_amount == expected_reserved
    
    @pytest.mark.django_db
    def test_buy_order_insufficient_funds(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """BUY order fails with insufficient funds."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with pytest.raises(ValueError, match="Insufficient funds"):
                place_stock_buy_order(
                    user_id=user.id,
                    stock=stock,
                    quantity=Decimal('1000000'),
                    order_type=OrderType.MARKET,
                )
    
    @pytest.mark.django_db
    def test_buy_order_inactive_asset_becomes_pending(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """BUY order becomes pending for inactive asset."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['GOOGL']  # Inactive in test setup
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('5'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.PENDING


class TestSellOrderPlacement:
    """Tests for SELL order placement."""
    
    @pytest.mark.django_db
    def test_market_sell_order_executes_when_market_open(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Market SELL order executes immediately when exchange is open."""
        user, wallets, position = user_with_position
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        initial_quantity = position.quantity
        
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_sell_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('20'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.FILLED
        
        # Check position was updated
        position.refresh_from_db()
        assert position.quantity == initial_quantity - Decimal('20')
        assert position.pending_quantity == Decimal('0')
        
        # Check realized P&L was calculated
        # Bought at 140, selling at current price
        expected_pnl = (stock_price - Decimal('140')) * Decimal('20')
        total_value = Decimal('20') * stock_price
        fee = (total_value * TRADING_FEE_PERCENTAGE).quantize(Decimal('0.01'))
        expected_pnl -= fee
        assert position.realized_pnl == expected_pnl
        
        # Check wallet balance increased (minus fee)
        usd_wallet.refresh_from_db()
        net_proceeds = total_value - fee
        assert usd_wallet.balance == initial_balance + net_proceeds
    
    @pytest.mark.django_db
    def test_market_sell_order_pending_when_market_closed(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Market SELL order becomes pending when exchange is closed."""
        user, wallets, position = user_with_position
        stock = market_data['stocks']['AAPL']
        initial_quantity = position.quantity
        
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_stock_sell_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('20'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Shares should be reserved
        position.refresh_from_db()
        assert position.quantity == initial_quantity  # Not sold yet
        assert position.pending_quantity == Decimal('20')
        assert position.available_quantity == initial_quantity - Decimal('20')
    
    @pytest.mark.django_db
    def test_sell_order_insufficient_holdings(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """SELL order fails with insufficient holdings."""
        user, wallets, position = user_with_position
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with pytest.raises(ValueError, match="Insufficient holdings"):
                place_stock_sell_order(
                    user_id=user.id,
                    stock=stock,
                    quantity=Decimal('200'),  # More than position.quantity (100)
                    order_type=OrderType.MARKET,
                )
    
    @pytest.mark.django_db
    def test_sell_order_no_position(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """SELL order fails when user has no position."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with pytest.raises(LookupError, match="No position found"):
                place_stock_sell_order(
                    user_id=user.id,
                    stock=stock,
                    quantity=Decimal('10'),
                    order_type=OrderType.MARKET,
                )
    
    @pytest.mark.django_db
    def test_limit_sell_order_executes_when_price_met(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """LIMIT SELL order executes when market price >= limit price."""
        user, wallets, position = user_with_position
        stock = market_data['stocks']['AAPL']
        
        current_price = stock.get_latest_price()
        assert current_price is not None
        
        # Set limit price below current price (should execute)
        limit_price = current_price - Decimal('10')
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_sell_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.LIMIT,
                limit_price=limit_price,
            )
        
        assert order.status == OrderStatus.FILLED
        
        trade = Trade.objects.get(order=order)
        assert trade.price == limit_price


class TestOrderCancellation:
    """Tests for order cancellation."""
    
    @pytest.mark.django_db
    def test_cancel_pending_buy_order_releases_funds(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cancelling a pending BUY order releases reserved funds."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_available = usd_wallet.available_balance
        
        # Create pending order
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.PENDING
        usd_wallet.refresh_from_db()
        assert usd_wallet.pending_balance > Decimal('0')
        
        # Cancel the order
        cancelled_order = cancel_order(order.id, user.id)
        
        assert cancelled_order.status == OrderStatus.CANCELLED
        assert cancelled_order.cancelled_at is not None
        
        # Funds should be released
        usd_wallet.refresh_from_db()
        assert usd_wallet.pending_balance == Decimal('0')
        assert usd_wallet.available_balance == initial_available
    
    @pytest.mark.django_db
    def test_cancel_pending_sell_order_releases_shares(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cancelling a pending SELL order releases reserved shares."""
        user, wallets, position = user_with_position
        stock = market_data['stocks']['AAPL']
        initial_available = position.available_quantity
        
        # Create pending order
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_stock_sell_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('20'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.PENDING
        position.refresh_from_db()
        assert position.pending_quantity == Decimal('20')
        
        # Cancel the order
        cancelled_order = cancel_order(order.id, user.id)
        
        assert cancelled_order.status == OrderStatus.CANCELLED
        
        # Shares should be released
        position.refresh_from_db()
        assert position.pending_quantity == Decimal('0')
        assert position.available_quantity == initial_available
    
    @pytest.mark.django_db
    def test_cannot_cancel_filled_order(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cannot cancel an already filled order."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('5'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.FILLED
        
        with pytest.raises(ValueError, match="Cannot cancel order"):
            cancel_order(order.id, user.id)
    
    @pytest.mark.django_db
    def test_cancel_nonexistent_order(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cancelling non-existent order raises LookupError."""
        user, wallets = user_with_wallets
        
        with pytest.raises(LookupError, match="Order not found"):
            cancel_order(99999, user.id)


class TestPendingOrderExecution:
    """Tests for executing pending orders."""
    
    @pytest.mark.django_db
    def test_execute_pending_buy_order(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Execute a pending BUY order when market opens."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        # Create pending order
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET,
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Execute when market opens
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            trade = execute_pending_order(order.id)
        
        assert trade is not None
        
        order.refresh_from_db()
        assert order.status == OrderStatus.FILLED
    
    @pytest.mark.django_db
    def test_execute_pending_limit_order_price_condition(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Pending LIMIT order only executes when price condition is met."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        current_price = stock.get_latest_price()
        assert current_price is not None
        
        # Set limit price below current price
        limit_price = current_price - Decimal('50')
        
        # Create pending limit order
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.LIMIT,
                limit_price=limit_price,
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Try to execute - should fail because price condition not met
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            trade = execute_pending_order(order.id)
        
        assert trade is None  # Did not execute
        
        order.refresh_from_db()
        assert order.status == OrderStatus.PENDING
        
        # Now update price to meet condition
        PriceHistory.objects.create(
            asset=stock,
            price=limit_price - Decimal('5'),  # Below limit price
            source='SIMULATION',
        )
        
        # Try again
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            trade = execute_pending_order(order.id)
        
        assert trade is not None
        
        order.refresh_from_db()
        assert order.status == OrderStatus.FILLED


class TestPositionManagement:
    """Tests for position updates."""
    
    @pytest.mark.django_db
    def test_position_weighted_average_cost(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Additional buys update average cost using weighted average."""
        user, wallets, position = user_with_position
        stock = market_data['stocks']['AAPL']
        
        # Initial: 100 shares @ $140
        initial_qty = position.quantity
        initial_avg = position.average_cost
        
        new_price = Decimal('160.00')
        new_qty = Decimal('50')
        
        # Update price
        PriceHistory.objects.create(
            asset=stock,
            price=new_price,
            source='SIMULATION',
        )
        
        # Buy more shares at the new price
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=new_qty,
                order_type=OrderType.MARKET,
            )
        
        position.refresh_from_db()
        
        # Check weighted average
        # (100 * 140 + 50 * 160) / 150 = (14000 + 8000) / 150 = 146.67
        expected_avg = (initial_qty * initial_avg + new_qty * new_price) / (initial_qty + new_qty)
        assert position.average_cost == expected_avg.quantize(Decimal('0.00000001'))
        assert position.quantity == initial_qty + new_qty


class TestQueryFunctions:
    """Tests for query/helper functions."""
    
    @pytest.mark.django_db
    def test_get_user_pending_orders(
        self,
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Get user's pending orders."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        # Create some pending orders
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order1 = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('5'),
                order_type=OrderType.MARKET,
            )
            order2 = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET,
            )
        
        pending = get_user_pending_orders(user.id)
        
        assert len(pending) == 2
        assert all(o.status == OrderStatus.PENDING for o in pending)
    
    @pytest.mark.django_db
    def test_get_user_positions(
        self,
        user_with_position: Tuple[CustomUser, QuerySet[Wallet], Position],
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Get user's open positions."""
        user, wallets, position = user_with_position
        
        positions = get_user_positions(user.id)
        
        assert len(positions) == 1
        assert positions[0].asset.id == position.asset.id  # Compare by ID due to model inheritance
        assert positions[0].quantity > 0
