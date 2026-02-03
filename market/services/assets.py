from django.db import transaction

from ..models import Asset, Currency, Exchange


@transaction.atomic
def create_stock_asset(symbol: str, name: str, exchange: Exchange, currency: Currency) -> Asset:
    stock = Asset.objects.create(
        asset_type="STOCK",
        ticker=symbol,
        name=name,
        currency=currency,
        exchange=exchange,
    )
    return stock
