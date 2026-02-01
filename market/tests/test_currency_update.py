from typing import Any
import pytest
from decimal import Decimal

from market.models import Currency, FXRate
from market.services import update_currency_prices
from market.tests.factories import CurrencyFactory


def test_update_currency_prices_success(market_data: dict[str, dict[str, Any]]) -> None:
    """Test successful currency price update with valid API response."""
    base_currency = market_data['currencies']['GBP']
    usd_currency = market_data['currencies']['USD']
    eur_currency = market_data['currencies']['EUR']
    
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {
            'GBPUSD': 1.39,
            'GBPEUR': 1.17,
        }
    }
    currencies_updated = update_currency_prices(dummy_api_response)

    assert currencies_updated == 2

    usd_rate = FXRate.objects.get(base_currency=base_currency, target_currency=usd_currency)
    eur_rate = FXRate.objects.get(base_currency=base_currency, target_currency=eur_currency)

    assert usd_rate.rate == Decimal('1.390000')
    assert eur_rate.rate == Decimal('1.170000')


def test_update_currency_prices_no_quotes(market_data: dict[str, dict[str, Any]]) -> None:
    """Test currency price update with empty quotes."""
    dummy_api_response = {
        'success': True,
        'timestamp': 1625247600,
        'source': 'GBP',
        'quotes': {}
    }

    currencies_updated = update_currency_prices(dummy_api_response)

    assert currencies_updated == 0


def test_update_currency_prices_partial_quotes(market_data: dict[str, dict[str, Any]]) -> None:
    """Test currency price update when only some assets have quotes."""
    base_currency = market_data['currencies']['GBP']

    usd_currency = market_data['currencies']['USD']
    eur_currency = market_data['currencies']['EUR']
    jpy_currency: Currency = CurrencyFactory(code='JPY', name='Japanese Yen', is_base=False)  # type: ignore[no-untyped-call, assignment]
    
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
    currencies_updated = update_currency_prices(dummy_api_response)

    assert currencies_updated == 2
    assert FXRate.objects.filter(base_currency=base_currency, target_currency=usd_currency).exists()
    assert FXRate.objects.filter(base_currency=base_currency, target_currency=eur_currency).exists()
    assert not FXRate.objects.filter(base_currency=base_currency, target_currency=jpy_currency).exists()