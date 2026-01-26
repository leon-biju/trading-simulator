import pytest
from unittest.mock import patch

from typing import Any, Tuple
from decimal import Decimal
from django.db.models import QuerySet
from django.contrib.auth import get_user_model
from market.models import Stock, Exchange
from trading.models import OrderSide, OrderType, OrderStatus
from accounts.models import CustomUser
from wallets.models import Wallet

from trading.services import place_stock_buy_order 

# Create a dummy user for testing
@pytest.fixture
def user_with_wallets(market_data: dict[str, dict[str, Any]]) -> Tuple[CustomUser, QuerySet[Wallet]]:
    User = get_user_model()
    user = User.objects.create_user(username='testuser', email='test@example.com', password='StrongV3ryStrongPasswd!')
    wallets = Wallet.objects.filter(user=user)
    
    # Add USD funds for stock trading (stocks are priced in USD)
    usd_wallet = wallets.get(currency__code='USD')
    usd_wallet.balance = Decimal('100000.00')
    usd_wallet.save()
    
    return user, wallets

@pytest.fixture
def inactive_stock(market_data: dict[str, dict[str, Any]]) -> Stock:
    stock: Stock = market_data['stocks']['AAPL']
    stock.is_active = False
    stock.save()
    return stock

# Trading Order Scenarios to test:
# 1. Placing a BUY order with sufficient funds.
@pytest.mark.django_db
def test_place_buy_order_with_sufficient_funds(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    # Expectation: Order is created and executed successfully.
    user, wallets = user_with_wallets
    stock = market_data['stocks']['AAPL']
    
    # Get initial balances
    usd_wallet = wallets.get(currency=stock.currency)
    initial_balance = usd_wallet.balance
    stock_price = stock.get_latest_price()
    assert stock_price is not None
    
    with patch.object(Exchange, 'is_currently_open', return_value=True):
        order = place_stock_buy_order(
            user_id=user.id,
            stock=stock,
            quantity=Decimal('10'),
            order_type=OrderType.MARKET
        )
    
    assert order is not None
    assert order.side == OrderSide.BUY
    assert order.quantity == Decimal('10')
    assert order.status == OrderStatus.FILLED
    
    # Refresh wallet and check balance was deducted (with fee)
    usd_wallet.refresh_from_db()
    expected_cost = Decimal('10') * stock_price
    expected_fee = (expected_cost * Decimal('0.001')).quantize(Decimal('0.01'))
    expected_total = expected_cost + expected_fee
    assert usd_wallet.balance == initial_balance - expected_total
    assert usd_wallet.pending_balance == Decimal('0')  # No pending after execution


# 2. Placing a BUY order with insufficient funds.
@pytest.mark.django_db
def test_place_buy_order_with_insufficient_funds(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    stock = market_data['stocks']['AAPL']
    with patch.object(Exchange, 'is_currently_open', return_value=True):
        with pytest.raises(ValueError, match=f"Insufficient funds in {stock.currency.code} wallet"):
            order = place_stock_buy_order(
                user_id=user.id,
                stock=stock,
                quantity=Decimal('1000000'),  # Excessive quantity to trigger insufficient funds
                order_type=OrderType.MARKET
            )


# 3. Placing a BUY order when the market is closed.
@pytest.mark.django_db
def test_place_buy_order_when_market_closed(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    usd_wallet = wallets.get(currency_id=market_data['currencies']['USD'].id)
    initial_balance = usd_wallet.balance
    stock = market_data['stocks']['MSFT']  # Assuming MSFT is on a closed exchange in test setup
    stock_price = stock.get_latest_price()
    assert stock_price is not None
    
    with patch.object(Exchange, 'is_currently_open', return_value=False):
        order = place_stock_buy_order(
            user_id=user.id,
            stock=stock,
            quantity=Decimal('10'),
            order_type=OrderType.MARKET
        )

    assert order is not None
    assert order.side == OrderSide.BUY
    assert order.quantity == Decimal('10')
    assert order.status == OrderStatus.PENDING
    
    # Check funds are reserved (pending_balance increased, balance unchanged)
    usd_wallet.refresh_from_db()
    expected_reserved = (Decimal('10') * stock_price).quantize(Decimal('0.01'))
    assert usd_wallet.balance == initial_balance  # Balance not changed until execution
    assert usd_wallet.pending_balance == expected_reserved
    assert usd_wallet.available_balance == initial_balance - expected_reserved

        
# 4. Placing a LIMIT BUY order with a specified limit price.
# 5. Placing an order for an inactive asset.
# 6. Placing a SELL order with sufficient holdings.
# 7. Placing a SELL order with insufficient holdings.
# 8. Placing a LIMIT SELL order with a specified limit price.
