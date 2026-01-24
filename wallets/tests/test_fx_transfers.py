from typing import Any, Tuple
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from accounts.models import CustomUser
from market.models import Currency
from wallets.models import Fx_Transfer, Wallet, Transaction
from wallets.services import perform_fx_transfer


@pytest.fixture
def user_with_wallets(market_data: dict[str, dict[str, Any]]) -> Tuple[CustomUser, QuerySet[Wallet]]:
    """Create a test user with wallets after market data is set up."""
    user = CustomUser.objects.create_user(
        username='testuser', 
        email='test@example.com', 
        password='StrongV3ryStrongPasswd!'
    )
    wallets = Wallet.objects.filter(user=user)
    return user, wallets


def test_fx_transfer_success(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    gbp_cur = market_data['currencies']['GBP']
    usd_cur = market_data['currencies']['USD']
    gbp_wallet = wallets.get(currency=gbp_cur)
    usd_wallet = wallets.get(currency=usd_cur)

    initial_gbp_balance = gbp_wallet.balance
    initial_usd_balance = usd_wallet.balance

    from_amount = Decimal('1000.00')

    exchange_rate = market_data['fx_rates']['USD'] / market_data['fx_rates']['GBP']

    fx_transfer = perform_fx_transfer(
        user_id=user.id,
        from_wallet_currency_code='GBP',
        to_wallet_currency_code='USD',
        from_amount=from_amount
    )

    assert fx_transfer is not None

    gbp_wallet.refresh_from_db()
    usd_wallet.refresh_from_db()

    assert gbp_wallet.balance == initial_gbp_balance - from_amount
    assert usd_wallet.balance == initial_usd_balance + (from_amount * exchange_rate)

    assert fx_transfer.from_wallet == gbp_wallet
    assert fx_transfer.to_wallet == usd_wallet

    assert fx_transfer.from_amount == from_amount
    assert fx_transfer.to_amount == from_amount * exchange_rate
    assert fx_transfer.exchange_rate == exchange_rate

    # Check transactions created
    gbp_transactions = gbp_wallet.transactions.filter(source='FX_TRANSFER')
    usd_transactions = usd_wallet.transactions.filter(source='FX_TRANSFER')

    assert gbp_transactions.count() == 1
    assert usd_transactions.count() == 1

    gbp_transaction = gbp_transactions.first()
    usd_transaction = usd_transactions.first()

    assert gbp_transaction is not None
    assert usd_transaction is not None

    assert gbp_transaction.amount == -from_amount
    assert usd_transaction.amount == from_amount * exchange_rate


def test_fx_transfer_insufficient_funds(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    initial_transactions_count = Transaction.objects.filter(wallet__user=user).count()
    gbp_cur = market_data['currencies']['GBP']
    usd_cur = market_data['currencies']['USD']
    gbp_wallet = wallets.get(currency=gbp_cur)
    usd_wallet = wallets.get(currency=usd_cur)

    from_amount = gbp_wallet.balance + Decimal('1000.00')  # More than available
    
    with pytest.raises(ValueError, match="Insufficient funds in from_wallet"):
        perform_fx_transfer(
            user_id=user.id,
            from_wallet_currency_code='GBP',
            to_wallet_currency_code='USD',
            from_amount=from_amount
        )
    
    # Verify no new transactions were created
    assert Transaction.objects.filter(wallet__user=user).count() == initial_transactions_count