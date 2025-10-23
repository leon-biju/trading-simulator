from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from apps.wallets.models import Wallet, Currency

# Create a dummy user for testing
@pytest.fixture
def user_with_wallets():
    User = get_user_model()
    user = User.objects.create_user(username='testuser', email='test@example.com', password='StrongV3ryStrongPasswd!')
    wallets = Wallet.objects.filter(user=user)
    return user, wallets

@pytest.mark.django_db
def test_all_wallets_created_for_new_user(user_with_wallets):
    user, wallets = user_with_wallets
    assert wallets.count() == len(Currency.choices)
    
    created_currencies = {wallet.currency for wallet in wallets}
    expected_currencies = {currency[0] for currency in Currency.choices}
    assert created_currencies == expected_currencies

    for wallet in wallets:
        assert wallet.user == user

@pytest.mark.django_db
def test_gbp_wallet_initial_balance(user_with_wallets):
    user, wallets = user_with_wallets
    gbp_wallet = wallets.get(currency='GBP')
    assert gbp_wallet.balance == Decimal('100000.00')