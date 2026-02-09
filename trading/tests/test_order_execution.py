"""
Comprehensive tests for trading order execution.

Tests cover:
- Order execution (BUY/SELL)
- Position management
- Order cancellation
- LIMIT order conditions
- Error handling
"""
import pytest
from unittest.mock import patch
from typing import Any, Tuple
from decimal import Decimal

from django.db.models import QuerySet
from django.contrib.auth import get_user_model

from market.models import Exchange
from trading.models import OrderSide, OrderStatus, OrderType, Position, Trade

from trading.services.orders import  place_order, cancel_order
from trading.services.utils import TRADING_FEE_PERCENTAGE
from trading.services.execution import execute_order, execute_pending_order

from accounts.models import CustomUser
from wallets.models import Wallet, Transaction


@pytest.fixture
def user_with_wallets(market_data: dict[str, dict[str, Any]]) -> Tuple[CustomUser, QuerySet[Wallet]]:
    """Create a test user with wallets."""
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
) -> Tuple[CustomUser, Position]:
    """Create a test user with an existing position in AAPL."""
    user, wallets = user_with_wallets
    stock = market_data['stocks']['AAPL']
    
    # Create a position directly
    position = Position.objects.create(
        user=user,
        asset=stock,
        quantity=Decimal('100'),
        pending_quantity=Decimal('0'),
        average_cost=Decimal('140.00'),
        realized_pnl=Decimal('0'),
    )
    return user, position


class TestBuyOrderExecution:
    """Tests for BUY order execution."""
    
    @pytest.mark.django_db
    def test_market_buy_order_executed_when_market_open(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """MARKET BUY should execute immediately when market is open."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.FILLED
        
        # Check trade was created
        trade = Trade.objects.get(order=order)
        assert trade.quantity == Decimal('10')
        assert trade.price == stock_price
        assert trade.fee == (Decimal('10') * stock_price * TRADING_FEE_PERCENTAGE).quantize(Decimal('0.01'))
        
        # Check position was created
        position = Position.objects.get(user=user, asset=stock)
        assert position.quantity == Decimal('10')
        assert position.average_cost == stock_price
        
        # Check wallet was updated
        usd_wallet.refresh_from_db()
        expected_cost = (Decimal('10') * stock_price * (1 + TRADING_FEE_PERCENTAGE)).quantize(Decimal('0.01'))
        assert usd_wallet.balance == initial_balance - expected_cost
        assert usd_wallet.pending_balance == Decimal('0')
        
        # Check transaction was created
        tx = Transaction.objects.get(wallet=usd_wallet, source=Transaction.Source.BUY)
        assert tx.amount < 0  # Debit

    @pytest.mark.django_db
    def test_market_buy_order_pending_when_market_closed(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """MARKET BUY should be PENDING when market is closed."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Check funds were reserved
        expected_reserved = (Decimal('10') * stock_price).quantize(Decimal('0.01'))
        assert order.reserved_amount == expected_reserved
        
        usd_wallet.refresh_from_db()
        assert usd_wallet.balance == initial_balance  # Not deducted yet
        assert usd_wallet.pending_balance == expected_reserved
        assert usd_wallet.available_balance == initial_balance - expected_reserved

    @pytest.mark.django_db
    def test_limit_buy_order_pending_when_price_not_met(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """LIMIT BUY should be PENDING when limit price < market price."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        # Set limit price below current market price
        limit_price = stock_price - Decimal('10')
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('10'),
                order_type=OrderType.LIMIT,
                limit_price=limit_price
            )
        
        assert order.status == OrderStatus.PENDING
        assert order.limit_price == limit_price
        
        # Reserved at limit price, not market price
        expected_reserved = (Decimal('10') * limit_price).quantize(Decimal('0.01'))
        assert order.reserved_amount == expected_reserved


class TestSellOrderExecution:
    """Tests for SELL order execution."""
    
    @pytest.mark.django_db
    def test_market_sell_order_executed_when_market_open(
        self, 
        user_with_position: Tuple[CustomUser, Position], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """MARKET SELL should execute immediately when market is open."""
        user, position = user_with_position
        stock = market_data['stocks']['AAPL']
        wallet = Wallet.objects.get(user=user, currency=stock.currency)
        initial_balance = wallet.balance
        initial_quantity = position.quantity
        stock_price = stock.get_latest_price()
        assert stock_price is not None
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.SELL,
                quantity=Decimal('20'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.FILLED
        
        # Check trade was created
        trade = Trade.objects.get(order=order)
        assert trade.quantity == Decimal('20')
        assert trade.side == OrderSide.SELL
        
        # Check position was reduced
        position.refresh_from_db()
        assert position.quantity == initial_quantity - Decimal('20')
        
        # Check wallet was credited
        wallet.refresh_from_db()
        expected_proceeds = (Decimal('20') * stock_price * (1 - TRADING_FEE_PERCENTAGE)).quantize(Decimal('0.01'))
        assert wallet.balance == initial_balance + expected_proceeds

    @pytest.mark.django_db
    def test_sell_order_fails_without_holdings(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """SELL order should fail if user has no position."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with pytest.raises(LookupError, match=f"No position found for {stock.ticker}"):
                place_order(
                    user_id=user.id,
                    asset=stock,
                    side=OrderSide.SELL,
                    quantity=Decimal('10'),
                    order_type=OrderType.MARKET
                )

    @pytest.mark.django_db
    def test_sell_order_fails_with_insufficient_holdings(
        self, 
        user_with_position: Tuple[CustomUser, Position], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """SELL order should fail if quantity exceeds holdings."""
        user, position = user_with_position
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with pytest.raises(ValueError, match=f"Insufficient holdings of {stock.ticker}"):
                place_order(
                    user_id=user.id,
                    asset=stock,
                    side=OrderSide.SELL,
                    quantity=Decimal('200'),  # More than the 100 in position
                    order_type=OrderType.MARKET
                )

    @pytest.mark.django_db
    def test_pending_sell_reserves_shares(
        self, 
        user_with_position: Tuple[CustomUser, Position], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """PENDING SELL order should reserve shares."""
        user, position = user_with_position
        stock = market_data['stocks']['AAPL']
        initial_quantity = position.quantity
        
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.SELL,
                quantity=Decimal('30'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Check shares were reserved
        position.refresh_from_db()
        assert position.quantity == initial_quantity  # Total unchanged
        assert position.pending_quantity == Decimal('30')
        assert position.available_quantity == initial_quantity - Decimal('30')


class TestOrderCancellation:
    """Tests for order cancellation."""
    
    @pytest.mark.django_db
    def test_cancel_pending_buy_order_releases_funds(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cancelling PENDING BUY should release reserved funds."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Verify funds are reserved
        usd_wallet.refresh_from_db()
        assert usd_wallet.pending_balance > 0
        
        # Cancel the order
        cancelled_order = cancel_order(order.id, user.id)
        
        assert cancelled_order.status == OrderStatus.CANCELLED
        assert cancelled_order.cancelled_at is not None
        
        # Verify funds are released
        usd_wallet.refresh_from_db()
        assert usd_wallet.pending_balance == Decimal('0')
        assert usd_wallet.available_balance == initial_balance

    @pytest.mark.django_db
    def test_cancel_pending_sell_order_releases_shares(
        self, 
        user_with_position: Tuple[CustomUser, Position], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cancelling PENDING SELL should release reserved shares."""
        user, position = user_with_position
        stock = market_data['stocks']['AAPL']
        initial_quantity = position.quantity
        
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.SELL,
                quantity=Decimal('20'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Cancel the order
        cancelled_order = cancel_order(order.id, user.id)
        
        assert cancelled_order.status == OrderStatus.CANCELLED
        
        # Verify shares are released
        position.refresh_from_db()
        assert position.pending_quantity == Decimal('0')
        assert position.available_quantity == initial_quantity

    @pytest.mark.django_db
    def test_cannot_cancel_filled_order(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Cannot cancel an already FILLED order."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('5'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.FILLED
        
        with pytest.raises(ValueError, match="Cannot cancel order with status FILLED"):
            cancel_order(order.id, user.id)


class TestPendingOrderExecution:
    """Tests for executing pending orders (e.g., when market opens)."""
    
    @pytest.mark.django_db
    def test_execute_pending_buy_order(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Execute a pending BUY order when conditions are met."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        usd_wallet = wallets.get(currency=stock.currency)
        initial_balance = usd_wallet.balance
        
        # Create pending order (market closed)
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('10'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Now execute it (market open)
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            trade = execute_pending_order(order.id)
        
        assert trade is not None
        
        order.refresh_from_db()
        assert order.status == OrderStatus.FILLED
        
        # Verify position exists
        position = Position.objects.get(user=user, asset=stock)
        assert position.quantity == Decimal('10')
        usd_wallet.refresh_from_db()
        assert usd_wallet.balance < initial_balance  # Funds deducted

    @pytest.mark.django_db
    def test_execute_pending_sell_order(
        self, 
        user_with_position: Tuple[CustomUser, Position], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Execute a pending SELL order when conditions are met."""
        user, position = user_with_position
        stock = market_data['stocks']['AAPL']
        initial_quantity = position.quantity
        wallet = Wallet.objects.get(user=user, currency=stock.currency)
        initial_balance = wallet.balance
        
        # Create pending order (market closed)
        with patch.object(Exchange, 'is_currently_open', return_value=False):
            order = place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.SELL,
                quantity=Decimal('25'),
                order_type=OrderType.MARKET
            )
        
        assert order.status == OrderStatus.PENDING
        
        # Now execute it (market open)
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            trade = execute_pending_order(order.id)
        
        assert trade is not None
        
        order.refresh_from_db()
        assert order.status == OrderStatus.FILLED
        
        # Verify position was reduced
        position.refresh_from_db()
        assert position.quantity == initial_quantity - Decimal('25')
        assert position.pending_quantity == Decimal('0')
        
        # Verify wallet was credited
        wallet.refresh_from_db()
        assert wallet.balance > initial_balance


class TestPositionAverageCost:
    """Tests for position average cost calculations."""
    
    @pytest.mark.django_db
    def test_weighted_average_cost_on_multiple_buys(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Average cost should be weighted average across multiple buys."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        # First buy at $150
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with patch.object(stock, 'get_latest_price', return_value=Decimal('150.00')):
                place_order(
                    user_id=user.id,
                    asset=stock,
                    side=OrderSide.BUY,
                    quantity=Decimal('10'),
                    order_type=OrderType.MARKET
                )
        
        position = Position.objects.get(user=user, asset=stock)
        assert position.quantity == Decimal('10')
        assert position.average_cost == Decimal('150.00')
        
        # Second buy at $160
        with patch.object(Exchange, 'is_currently_open', return_value=True):
            with patch.object(stock, 'get_latest_price', return_value=Decimal('160.00')):
                place_order(
                    user_id=user.id,
                    asset=stock,
                    side=OrderSide.BUY,
                    quantity=Decimal('10'),
                    order_type=OrderType.MARKET
                )
        
        position.refresh_from_db()
        assert position.quantity == Decimal('20')
        # Weighted avg: (10*150 + 10*160) / 20 = 155
        assert position.average_cost == Decimal('155.00000000')


class TestInputValidation:
    """Tests for input validation."""
    
    @pytest.mark.django_db
    def test_negative_quantity_rejected(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """Negative quantity should be rejected."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with pytest.raises(ValueError, match="Quantity must be positive"):
            place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('-10'),
                order_type=OrderType.MARKET
            )

    @pytest.mark.django_db
    def test_limit_order_requires_price(
        self, 
        user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], 
        market_data: dict[str, dict[str, Any]]
    ) -> None:
        """LIMIT order without price should be rejected."""
        user, wallets = user_with_wallets
        stock = market_data['stocks']['AAPL']
        
        with pytest.raises(ValueError, match="Limit price is required"):
            place_order(
                user_id=user.id,
                asset=stock,
                side=OrderSide.BUY,
                quantity=Decimal('10'),
                order_type=OrderType.LIMIT,
                limit_price=None
            )
