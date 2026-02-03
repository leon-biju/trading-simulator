# mypy: disable-error-code=assignment
# mypy: disable-error-code=no-untyped-def
# mypy: disable-error-code=no-untyped-call

from market.models import Asset, Currency, Exchange
from market.services.assets import create_stock_asset
from market.tests.factories import ExchangeFactory, CurrencyFactory


class TestAssetCreationServices:
    def test_create_stock_asset(self, db):
        """
        Test that `create_stock_asset` service function correctly creates an Asset.
        """
        exchange: Exchange = ExchangeFactory()
        currency: Currency = CurrencyFactory()

        stock = create_stock_asset(
            symbol="AAPL",
            name="Apple Inc.",
            exchange=exchange,
            currency=currency,
        )

        assert isinstance(stock, Asset)
        assert stock.ticker == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.exchange == exchange
        assert stock.currency == currency
        assert stock.asset_type == "STOCK"
        assert Asset.objects.count() == 1
