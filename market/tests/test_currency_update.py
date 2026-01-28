from typing import Any
import pytest
from decimal import Decimal
import datetime

from market.models import PriceCandle, CurrencyAsset
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
    expected_bucket = expected_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

    currencies_updated = update_currency_prices(dummy_api_response)

    assert currencies_updated == 2 + 1 # Including base currency
    assert PriceCandle.objects.filter(
        start_at=expected_bucket,
        interval_minutes=1440,
    ).count() == 3

    
    # Verify USD price
    usd_price = PriceCandle.objects.get(
        asset=usd_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    )
    assert usd_price.close_price == Decimal('1.3900')
    assert usd_price.source == 'LIVE'
    assert usd_price.start_at == expected_bucket
    
    # Verify EUR price
    eur_price = PriceCandle.objects.get(
        asset=eur_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    )
    assert eur_price.close_price == Decimal('1.1700')
    assert eur_price.source == 'LIVE'
    assert eur_price.start_at == expected_bucket


def test_update_currency_prices_no_quotes(market_data: dict[str, dict[str, Any]]) -> None:
    """Test currency price update with empty quotes."""
    initial_count = PriceCandle.objects.count()
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {}
    }

    currencies_updated = update_currency_prices(dummy_api_response)

    expected_timestamp = datetime.datetime.fromtimestamp(1625247600, tz=datetime.timezone.utc)
    expected_bucket = expected_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    assert PriceCandle.objects.filter(
        start_at=expected_bucket,
        interval_minutes=1440,
    ).count() == 1
    
    base_currency_asset = CurrencyAsset.objects.get(symbol='GBP')
    base_price = PriceCandle.objects.get(
        asset=base_currency_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    )
    assert base_price.close_price == Decimal('1.0000')
    assert base_price.source == 'LIVE'
    assert base_price.start_at == expected_bucket


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
    expected_bucket = expected_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    currencies_updated = update_currency_prices(dummy_api_response)

    # Only active asset + gbp should be updated
    assert currencies_updated == 1 + 1

    assert PriceCandle.objects.filter(
        start_at=expected_bucket,
        interval_minutes=1440,
    ).count() == 2
    assert PriceCandle.objects.filter(
        asset=active_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    ).exists()
    assert not PriceCandle.objects.filter(
        asset=inactive_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    ).exists()


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
    expected_bucket = expected_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

    currencies_updated = update_currency_prices(dummy_api_response)

    # Only USD and EUR should be updated
    assert currencies_updated == 2 + 1 # Including base currency
    assert PriceCandle.objects.filter(
        start_at=expected_bucket,
        interval_minutes=1440,
    ).count() == 3
    assert PriceCandle.objects.filter(
        asset=usd_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    ).exists()
    assert PriceCandle.objects.filter(
        asset=eur_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    ).exists()
    assert not PriceCandle.objects.filter(
        asset=jpy_asset,
        interval_minutes=1440,
        start_at=expected_bucket,
    ).exists()