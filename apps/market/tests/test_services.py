import pytest
from django.core.exceptions import ObjectDoesNotExist

from apps.market.models import Currency, Stock, CurrencyAsset
from apps.market.services import create_stock_asset, create_currency_asset
from apps.market.tests.factories import ExchangeFactory, CurrencyFactory

pytestmark = pytest.mark.django_db


class TestAssetCreationServices:
    def test_create_stock_asset(self):
        """
        Test that `create_stock_asset` service function correctly creates a Stock.
        """
        exchange = ExchangeFactory()
        currency = CurrencyFactory()

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

    def test_create_currency_asset(self):
        """
        Test that `create_currency_asset` service function correctly creates a CurrencyAsset
        and assigns the base currency.
        """
        # Ensure a base currency exists
        base_currency = CurrencyFactory(is_base=True)
        CurrencyFactory(is_base=False)  # Create another non-base currency

        currency_asset = create_currency_asset(
            symbol="EUR",
            name="Euro",
        )

        assert isinstance(currency_asset, CurrencyAsset)
        assert currency_asset.symbol == "EUR"
        assert currency_asset.name == "Euro"
        assert currency_asset.currency == base_currency
        assert currency_asset.asset_type == "CURRENCY"
        assert CurrencyAsset.objects.count() == 1

    def test_create_currency_asset_raises_error_if_no_base_currency(self):
        """
        Test that `create_currency_asset` raises an exception if no base currency is defined.
        """
        with pytest.raises(ObjectDoesNotExist):
            create_currency_asset(
                symbol="EUR",
                name="Euro",
            )
        
        assert CurrencyAsset.objects.count() == 0
