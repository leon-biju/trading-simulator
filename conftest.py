import pytest
from test_framework import (
    setup_currencies,
    setup_currency_assets,
    setup_fx_rates,
    setup_complete_market_data,
)


@pytest.fixture
def currencies(db):
    """
    Fixture that creates standard test currencies.
    Usage: def test_something(currencies):
    """
    return setup_currencies()


@pytest.fixture
def currency_assets(db, currencies):
    """
    Fixture that creates currency assets.
    Automatically depends on currencies fixture.
    Usage: def test_something(currency_assets):
    """
    return setup_currency_assets()


@pytest.fixture
def fx_rates(db, currency_assets):
    """
    Fixture that creates FX rates.
    Automatically depends on currency_assets fixture.
    Usage: def test_something(fx_rates):
    """
    return setup_fx_rates()


@pytest.fixture
def market_data(db):
    """
    Fixture that sets up complete market data (currencies, assets, and FX rates).
    Usage: def test_something(market_data):
    """
    return setup_complete_market_data()
