from django.contrib.auth import get_user_model
import pytest
from decimal import Decimal
from apps.trading.models import Wallet, CommissionRule
from apps.market.models import Instrument, Quote

from apps.trading.services import commisions

User = get_user_model()

@pytest.fixture
def basic_setup(db):
    # Minimal fixture for service tests.

    user = User.objects.create_user(username='test', email='test@test.com')

    gbp_wallet, _ = Wallet.objects.get_or_create(
        user=user,
        currency='GBP',
        defaults={'balance': Decimal('10000.00')}
    )

    gbp_wallet.balance = Decimal('10000.00')
    gbp_wallet.save()
    
    instrument = Instrument.objects.create(
        ticker='TEST.L',
        name='Test Stock',
        currency='GBP',
        tick_size=Decimal('0.01'),
        lot_size=1,
        active=True
    )
    
    Quote.objects.create(
        instrument=instrument,
        last_price=Decimal('1.00'),
        timestamp='2025-01-15T10:00:00Z'
    )
    
    CommissionRule.objects.create(
        name='Test Rule',
        rate_bps=Decimal('10.00'),
        min_fee=Decimal('1.00'),
        currency='GBP',
        active=True
    )
    
    return {
        'user': user,
        'wallet': gbp_wallet,
        'instrument': instrument
    }


@pytest.mark.django_db
def test_commission_calculation(basic_setup):
    """Test basic commission calculation."""
    price = Decimal('10.00')
    quantity = 100

    # Small trade
    commission = commisions.calculate(price, quantity, 'GBP')
    # 100 * 10 = 1000, 10bps of 1000 = 1.00, but min is 1.00
    assert commission == Decimal('1.00')
    
    # Larger trade
    commission = commisions.calculate(Decimal('100.00'), 1000, 'GBP')
    # 100 * 1000 = 100,000, 10bps of 100,000 = 100.00
    assert commission == Decimal('100.00')