# mypy: disable-error-code=assignment
# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

import pytest
from django.core.exceptions import ObjectDoesNotExist

from market.models import Currency, Stock, CurrencyAsset, Exchange
from market.services import create_stock_asset, create_currency_asset
from market.tests.factories import ExchangeFactory, CurrencyFactory


class TestAssetCreationServices:
    def test_create_stock_asset(self, db):
        """
        Test that `create_stock_asset` service function correctly creates a Stock.
        """
        exchange: Exchange = ExchangeFactory()
        currency: Currency = CurrencyFactory()

        stock = create_stock_asset(
            symbol="AAPL",
            name="Apple Inc.",
            exchange=exchange,
            currency=currency,
        )

        assert isinstance(stock, Stock)
        assert stock.symbol == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.exchange == exchange
        assert stock.currency == currency
        assert stock.asset_type == "STOCK"
        assert Stock.objects.count() == 1

    def test_create_currency_asset(self, market_data):
        """
        Test that `create_currency_asset` service function correctly creates a CurrencyAsset
        and assigns the base currency.
        """
        # Base currency already exists from market_data fixture
        base_currency = market_data['currencies']['GBP']

        currency_asset = create_currency_asset(
            symbol="XYZ",
            name="Fictional Currency",
        )

        assert isinstance(currency_asset, CurrencyAsset)
        assert currency_asset.symbol == "XYZ"
        assert currency_asset.name == "Fictional Currency"
        assert currency_asset.currency == base_currency
        assert currency_asset.asset_type == "CURRENCY"
        assert CurrencyAsset.objects.filter(symbol="XYZ").count() == 1

    def test_create_currency_asset_raises_error_if_no_base_currency(self, db):
        """
        Test that `create_currency_asset` raises an exception if no base currency is defined.
        """
        with pytest.raises(ObjectDoesNotExist):
            create_currency_asset(
                symbol="EUR",
                name="Euro",
            )
        
        assert CurrencyAsset.objects.count() == 0
