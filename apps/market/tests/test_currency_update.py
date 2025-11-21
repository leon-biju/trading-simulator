import pytest
from decimal import Decimal
import datetime

from apps.market.models import PriceHistory
from apps.market.services import update_currency_prices
from apps.market.tests.factories import CurrencyFactory, CurrencyAssetFactory


@pytest.mark.django_db
def test_update_currency_prices_success():
    """Test successful currency price update with valid API response."""
    # Create base currency (GBP in this case)
    base_currency = CurrencyFactory(code='GBP', name='British Pound', is_base=True)
    
    # Create currency assets (these are what get traded)
    usd_asset = CurrencyAssetFactory(symbol='USD', name='US Dollar', currency=base_currency, is_active=True)
    eur_asset = CurrencyAssetFactory(symbol='EUR', name='Euro', currency=base_currency, is_active=True)
    
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {
            'GBPUSD': 1.39,
            'GBPEUR': 1.17,
        }
    }

    status = update_currency_prices(dummy_api_response)

    assert status == "Updated prices for 2 currency assets."
    assert PriceHistory.objects.count() == 2
    
    # Verify USD price
    usd_price = PriceHistory.objects.get(asset=usd_asset)
    assert usd_price.price == Decimal('1.3900')
    assert usd_price.source == 'LIVE'
    expected_timestamp = datetime.datetime.fromtimestamp(1625247600, tz=datetime.timezone.utc)
    assert usd_price.timestamp == expected_timestamp
    
    # Verify EUR price
    eur_price = PriceHistory.objects.get(asset=eur_asset)
    assert eur_price.price == Decimal('1.1700')
    assert eur_price.source == 'LIVE'
    assert eur_price.timestamp == expected_timestamp


@pytest.mark.django_db
def test_update_currency_prices_no_quotes():
    """Test currency price update with empty quotes."""

    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {}
    }

    status = update_currency_prices(dummy_api_response)

    assert status == "No currency quotes found in the data."
    assert PriceHistory.objects.count() == 0


@pytest.mark.django_db
def test_update_currency_prices_inactive_assets():
    """Test that inactive currency assets are not updated."""
    base_currency = CurrencyFactory(code='GBP', name='British Pound', is_base=True)
    
    # Create active and inactive currency assets
    active_asset = CurrencyAssetFactory(symbol='USD', name='US Dollar', currency=base_currency, is_active=True)
    inactive_asset = CurrencyAssetFactory(symbol='EUR', name='Euro', currency=base_currency, is_active=False)
    
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {
            'GBPUSD': 1.39,
            'GBPEUR': 1.17,
        }
    }

    status = update_currency_prices(dummy_api_response)

    # Only active asset should be updated
    assert status == "Updated prices for 1 currency assets."
    assert PriceHistory.objects.count() == 1
    assert PriceHistory.objects.filter(asset=active_asset).exists()
    assert not PriceHistory.objects.filter(asset=inactive_asset).exists()


@pytest.mark.django_db
def test_update_currency_prices_partial_quotes():
    """Test currency price update when only some assets have quotes."""
    base_currency = CurrencyFactory(code='GBP', name='British Pound', is_base=True)
    
    # Create three currency assets
    usd_asset = CurrencyAssetFactory(symbol='USD', name='US Dollar', currency=base_currency, is_active=True)
    eur_asset = CurrencyAssetFactory(symbol='EUR', name='Euro', currency=base_currency, is_active=True)
    jpy_asset = CurrencyAssetFactory(symbol='JPY', name='Japanese Yen', currency=base_currency, is_active=True)
    
    # API response only contains quotes for USD and EUR (not JPY)
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {
            'GBPUSD': 1.39,
            'GBPEUR': 1.17,
        }
    }

    status = update_currency_prices(dummy_api_response)

    # Only USD and EUR should be updated
    assert status == "Updated prices for 2 currency assets."
    assert PriceHistory.objects.count() == 2
    assert PriceHistory.objects.filter(asset=usd_asset).exists()
    assert PriceHistory.objects.filter(asset=eur_asset).exists()
    assert not PriceHistory.objects.filter(asset=jpy_asset).exists()