# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import pytest
from test_framework import (
    setup_currencies,
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
def fx_rates(db, currencies):
    """
    Fixture that creates FX rates.
    Automatically depends on currencies fixture.
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
