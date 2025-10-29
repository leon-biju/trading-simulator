import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.wallets.models import Fx_Transfer, Wallet, Transaction
from apps.wallets import services

# These should always be used for testing FX transfers
DUMMY_FX_RATES = {
    'GBP': Decimal('1.0'),
    'USD': Decimal('1.25'),
    'EUR': Decimal('1.15'),
}

# Create a dummy user for testing
@pytest.fixture
def user_with_wallets():
    User = get_user_model()
    user = User.objects.create_user(username='testuser', email='test@example.com', password='StrongV3ryStrongPasswd!')
    wallets = Wallet.objects.filter(user=user)
    return user, wallets


@pytest.mark.django_db
def test_fx_transfer_success(user_with_wallets):
    user, wallets = user_with_wallets
    gbp_wallet = wallets.get(currency='GBP')
    usd_wallet = wallets.get(currency='USD')

    initial_gbp_balance = gbp_wallet.balance
    initial_usd_balance = usd_wallet.balance

    from_amount = Decimal('1000.00')

    exchange_rate = DUMMY_FX_RATES['USD'] / DUMMY_FX_RATES['GBP']

    fx_transfer, error = services.perform_fx_transfer(
        user_id=user.id,
        from_wallet_currency='GBP',
        to_wallet_currency='USD',
        from_amount=from_amount
    )

    assert error is None
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

    assert gbp_transactions.first().amount == -from_amount
    assert usd_transactions.first().amount == from_amount * exchange_rate

@pytest.mark.django_db
def test_fx_transfer_insufficient_funds(user_with_wallets):
    user, wallets = user_with_wallets
    initial_transactions_count = Transaction.objects.filter(wallet__user=user).count()
    gbp_wallet = wallets.get(currency='GBP')
    usd_wallet = wallets.get(currency='USD')

    from_amount = gbp_wallet.balance + Decimal('1000.00')  # More than available

    fx_transfer, error = services.perform_fx_transfer(
        user_id=user.id,
        from_wallet_currency='GBP',
        to_wallet_currency='USD',
        from_amount=from_amount
    )

    assert fx_transfer is None
    assert error == "INSUFFICIENT_FUNDS_IN_FROM_WALLET"
    
    # Verify no new transactions were created
    assert Transaction.objects.filter(wallet__user=user).count() == initial_transactions_count