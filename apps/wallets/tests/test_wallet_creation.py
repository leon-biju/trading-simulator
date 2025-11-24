from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from apps.wallets.models import Wallet
from apps.market.models import Currency

# Create a dummy user for testing
@pytest.fixture
def user_with_wallets(market_data):
    User = get_user_model()
    user = User.objects.create_user(username='testuser', email='test@example.com', password='StrongV3ryStrongPasswd!')
    wallets = Wallet.objects.filter(user=user)
    return user, wallets

@pytest.mark.django_db
def test_all_wallets_created_for_new_user(user_with_wallets, market_data):
    user, wallets = user_with_wallets
    assert wallets.count() == Currency.objects.count()  
    
    created_currencies = {wallet.currency for wallet in wallets}
    expected_currencies = {currency for currency in Currency.objects.all()}
    assert created_currencies == expected_currencies

    for wallet in wallets:
        assert wallet.user == user

@pytest.mark.django_db
def test_gbp_wallet_initial_balance(user_with_wallets, market_data):
    user, wallets = user_with_wallets
    base_currency = Currency.objects.filter(is_base=True).first()
    base_wallet = wallets.get(currency=base_currency)
    assert base_wallet.balance == Decimal('100000.00')