from decimal import Decimal
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.wallets.models import Transaction, Wallet
from apps.wallets import services

# Create a dummy user and default wallet for testing
@pytest.fixture
def user_with_wallet():
    User = get_user_model()
    user = User.objects.create_user(username='testuser', email='test@example.com', password='StrongV3ryStrongPasswd!')
    wallet = Wallet.objects.get(user=user, currency='GBP')
    return user, wallet

# 1. Test Wallet creation
@pytest.mark.django_db
def test_wallet_creation(user_with_wallet):
    user, wallet = user_with_wallet
    assert wallet is not None
    assert wallet.user == user


# 2. Test transaction creation and balance update on positive transaction
@pytest.mark.django_db
def test_transaction_creation_and_balance_update(user_with_wallet):
    user, wallet = user_with_wallet
    old_balance = wallet.balance
    transaction, error = services.create_transaction(
        wallet_id=wallet.id,
        amount=Decimal('10.98'),
        source=Transaction.Source.DEPOSIT,
        description="Initial deposit"
    )
    assert error is None

    assert transaction is not None
    wallet.refresh_from_db()
    assert transaction.amount == Decimal('10.98')
    assert wallet.balance == old_balance + Decimal('10.98')


# 3. Test transaction creation with insufficient funds
@pytest.mark.django_db
def test_transaction_creation_insufficient_funds(user_with_wallet):
    user, wallet = user_with_wallet
    wallet.balance = Decimal('50.00')
    wallet.save()
    transaction, error = services.create_transaction(
        wallet_id=wallet.id,
        amount=Decimal('-100.00'),
        source=Transaction.Source.WITHDRAWAL,
        description="Attempted overdraw"
    )
    assert transaction is None
    assert error == "INSUFFICIENT_FUNDS"
    wallet.refresh_from_db()
    assert wallet.balance == Decimal('50.00') # Balance should remain unchanged