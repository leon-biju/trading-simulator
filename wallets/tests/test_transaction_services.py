from typing import Any, Tuple
from decimal import Decimal
import pytest
from django.db.models import QuerySet
from accounts.models import CustomUser
from wallets.models import Transaction, Wallet
from wallets import services
import threading


# Create a dummy user for testing
@pytest.fixture
def user_with_wallets(market_data: dict[str, dict[str, Any]]) -> Tuple[CustomUser, QuerySet[Wallet]]:
    user = CustomUser.objects.create_user(username='testuser', email='test@example.com', password='StrongV3ryStrongPasswd!')
    wallets = Wallet.objects.filter(user=user)
    return user, wallets


@pytest.mark.django_db
def test_transaction_creation_and_balance_update(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    wallet = wallets.first()
    assert wallet is not None
    old_balance = wallet.balance
    transaction = services.create_transaction(
        wallet=wallet,
        amount=Decimal('10.98'),
        source=Transaction.Source.DEPOSIT,
        description="Initial deposit"
    )

    assert transaction is not None
    wallet.refresh_from_db()
    assert transaction.amount == Decimal('10.98')
    assert wallet.balance == old_balance + Decimal('10.98')


@pytest.mark.django_db
def test_transaction_creation_insufficient_funds(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    wallet = wallets.first()
    assert wallet is not None
    wallet.balance = Decimal('50.00')
    wallet.save()
    with pytest.raises(ValueError, match="Insufficient funds"):
        transaction = services.create_transaction(
            wallet=wallet,
            amount=Decimal('-100.00'),
            source=Transaction.Source.WITHDRAWAL,
            description="Attempted overdraw"
        )
    wallet.refresh_from_db()
    assert wallet.balance == Decimal('50.00')

@pytest.mark.django_db
def test_zero_amount_transaction(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    wallet = wallets.first()
    assert wallet is not None
    old_balance = wallet.balance
    with pytest.raises(ValueError, match="Zero-amount transaction"):
        transaction = services.create_transaction(
            wallet=wallet,
            amount=Decimal('0.00'),
            source=Transaction.Source.DEPOSIT,
            description="Zero amount transaction"
        )
    wallet.refresh_from_db()
    assert wallet.balance == old_balance

@pytest.mark.django_db
def test_transaction_data_integrity(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    wallet = wallets.first()
    assert wallet is not None
    transaction = services.create_transaction(
        wallet=wallet,
        amount=Decimal('25.50'),
        source=Transaction.Source.DEPOSIT,
        description="Data integrity test"
    )
    assert transaction is not None
    assert transaction.wallet == wallet
    assert transaction.amount == Decimal('25.50')
    assert transaction.source == Transaction.Source.DEPOSIT
    assert transaction.description == "Data integrity test"

@pytest.mark.django_db(transaction=True)
def test_concurrent_transactions_atomicity(user_with_wallets: Tuple[CustomUser, QuerySet[Wallet]], market_data: dict[str, dict[str, Any]]) -> None:
    user, wallets = user_with_wallets
    wallet = wallets.first()
    assert wallet is not None

    wallet.balance = Decimal('100.00')
    wallet.save()

    def make_transaction(amount: str) -> None:
        from django.db import connection
        services.create_transaction(
            wallet=wallet,
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
