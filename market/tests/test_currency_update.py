from typing import Any
import pytest
from decimal import Decimal
import datetime

from market.models import PriceHistory, CurrencyAsset
from market.services import update_currency_prices
from market.tests.factories import CurrencyFactory, CurrencyAssetFactory


def test_update_currency_prices_success(market_data: dict[str, dict[str, Any]]) -> None:
    """Test successful currency price update with valid API response."""
    # Use currency assets from market_data
    usd_asset = market_data['currency_assets']['USD']
    eur_asset = market_data['currency_assets']['EUR']
    
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {
            'GBPUSD': 1.39,
            'GBPEUR': 1.17,
        }
    }
    expected_timestamp = datetime.datetime.fromtimestamp(1625247600, tz=datetime.timezone.utc)

    currencies_updated = update_currency_prices(dummy_api_response)

    assert currencies_updated == 2 + 1 # Including base currency
    #Only check recent entries
    assert PriceHistory.objects.filter(timestamp=expected_timestamp).count() == 3

    
    # Verify USD price
    usd_price = PriceHistory.objects.get(asset=usd_asset, timestamp=expected_timestamp)
    assert usd_price.price == Decimal('1.3900')
    assert usd_price.source == 'LIVE'
    assert usd_price.timestamp == expected_timestamp
    
    # Verify EUR price
    eur_price = PriceHistory.objects.get(asset=eur_asset, timestamp=expected_timestamp)
    assert eur_price.price == Decimal('1.1700')
    assert eur_price.source == 'LIVE'
    assert eur_price.timestamp == expected_timestamp


def test_update_currency_prices_no_quotes(db): # type: ignore[no-untyped-def]
    """Test currency price update with empty quotes."""

    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {}
    }

    currencies_updated = update_currency_prices(dummy_api_response)

    assert currencies_updated == 1 # Only base currency
    assert PriceHistory.objects.count() == 0


def test_update_currency_prices_inactive_assets(market_data: dict[str, dict[str, Any]]) -> None:
    """Test that inactive currency assets are not updated."""
    # Use existing assets and modify one to be inactive
    active_asset = market_data['currency_assets']['USD']
    inactive_asset = market_data['currency_assets']['EUR']
    inactive_asset.is_active = False
    inactive_asset.save()
    
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {
            'GBPUSD': 1.39,
            'GBPEUR': 1.17,
        }
    }
    expected_timestamp = datetime.datetime.fromtimestamp(1625247600, tz=datetime.timezone.utc)
    currencies_updated = update_currency_prices(dummy_api_response)

    # Only active asset + gbp should be updated
    assert currencies_updated == 1 + 1

    assert PriceHistory.objects.filter(timestamp=expected_timestamp).count() == 2
    assert PriceHistory.objects.filter(asset=active_asset, timestamp=expected_timestamp).exists()
    assert not PriceHistory.objects.filter(asset=inactive_asset, timestamp=expected_timestamp).exists()


def test_update_currency_prices_partial_quotes(market_data: dict[str, dict[str, Any]]) -> None:
    """Test currency price update when only some assets have quotes."""
    base_currency = market_data['currencies']['GBP']
    
    # Use existing assets and create an additional one
    usd_asset = market_data['currency_assets']['USD']
    eur_asset = market_data['currency_assets']['EUR']
    jpy_asset: CurrencyAsset = CurrencyAssetFactory(symbol='JPY', name='Japanese Yen', currency=base_currency, is_active=True) # type: ignore[no-untyped-call, assignment]
    
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
    expected_timestamp = datetime.datetime.fromtimestamp(1625247600, tz=datetime.timezone.utc)

    currencies_updated = update_currency_prices(dummy_api_response)

    # Only USD and EUR should be updated
    assert currencies_updated == 2 + 1 # Including base currency
    assert PriceHistory.objects.filter(timestamp=expected_timestamp).count() == 3
    assert PriceHistory.objects.filter(asset=usd_asset, timestamp=expected_timestamp).exists()
    assert PriceHistory.objects.filter(asset=eur_asset, timestamp=expected_timestamp).exists()
    assert not PriceHistory.objects.filter(asset=jpy_asset, timestamp=expected_timestamp).exists()