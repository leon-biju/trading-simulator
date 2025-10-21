from decimal import Decimal
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.wallets.models import Transaction, Wallet
from apps.wallets import services
import threading

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
    assert wallet.balance == Decimal('50.00')


# 4. Test transaction creation with non-existent wallet
@pytest.mark.django_db
def test_transaction_creation_non_existent_wallet():
    assert not Wallet.objects.filter(id=9999).exists()
    transaction, error = services.create_transaction(
        wallet_id=9999,  # Assuming this ID does not exist
        amount=Decimal('10.00'),
        source=Transaction.Source.DEPOSIT,
        description="Deposit to non-existent wallet"
    )
    assert transaction is None
    assert error == "WALLET_DOES_NOT_EXIST"


# 5. Test zero amount transaction
@pytest.mark.django_db
def test_zero_amount_transaction(user_with_wallet):
    user, wallet = user_with_wallet
    old_balance = wallet.balance
    transaction, error = services.create_transaction(
        wallet_id=wallet.id,
        amount=Decimal('0.00'),
        source=Transaction.Source.DEPOSIT,
        description="Zero amount transaction"
    )
    assert error == "ZERO_AMOUNT_TRANSACTION"
    assert transaction is None
    wallet.refresh_from_db()
    assert wallet.balance == old_balance

# 6. Test transaction data integrity
@pytest.mark.django_db
def test_transaction_data_integrity(user_with_wallet):
    user, wallet = user_with_wallet
    transaction, error = services.create_transaction(
        wallet_id=wallet.id,
        amount=Decimal('25.50'),
        source=Transaction.Source.DEPOSIT,
        description="Data integrity test"
    )
    assert error is None
    assert transaction is not None
    assert transaction.wallet == wallet
    assert transaction.amount == Decimal('25.50')
    assert transaction.source == Transaction.Source.DEPOSIT
    assert transaction.description == "Data integrity test"

# 7. Test multiple concurrent transactions to ensure atomicity
@pytest.mark.django_db(transaction=True)
def test_concurrent_transactions_atomicity(user_with_wallet):
    user, wallet = user_with_wallet

    wallet.balance = Decimal('100.00')
    wallet.save()

    def make_transaction(amount):
        from django.db import connection
        services.create_transaction(
            wallet_id=wallet.id,
            amount=Decimal(amount),
            source=Transaction.Source.DEPOSIT if Decimal(amount) > 0 else Transaction.Source.WITHDRAWAL,
            description="Concurrent transaction"
        )
        connection.close()

    threads = []
    for amt in ['30.00', '-20.00', '50.00', '-10.00']:
        t = threading.Thread(target=make_transaction, args=(amt,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    wallet.refresh_from_db()
    # Final balance should be 100+30-20+50-10 = 150
    assert wallet.balance == Decimal('150.00')