# mypy: disable-error-code=type-arg
# mypy: disable-error-code=no-untyped-call
# mypy: disable-error-code=attr-defined

import factory
from factory.django import DjangoModelFactory
import datetime

from market import models

class ExchangeFactory(DjangoModelFactory):
    class Meta:
        model = models.Exchange
        django_get_or_create = ('code',)

    name = factory.Faker('company')
    code = factory.Faker('lexify', text='????')
    timezone = 'UTC'
    open_time = datetime.time(9, 30)
    close_time = datetime.time(16, 0)

class CurrencyFactory(DjangoModelFactory):
    class Meta:
        model = models.Currency
        django_get_or_create = ('code',)

    code = factory.Faker('currency_code')
    name = factory.Faker('currency_name')
    is_base = False

class AssetFactory(DjangoModelFactory):
    class Meta:
        model = models.Asset
        abstract = True

    asset_type = 'STOCK'
    symbol = factory.Faker('lexify', text='????')
    name = factory.Faker('company')
    currency = factory.SubFactory(CurrencyFactory)
    is_active = True

class StockFactory(AssetFactory):
    class Meta:
        model = models.Stock
        django_get_or_create = ('symbol',)

    asset_type = 'STOCK'
    exchange = factory.SubFactory(ExchangeFactory)

class CurrencyAssetFactory(AssetFactory):
    class Meta:
        model = models.CurrencyAsset
        django_get_or_create = ('symbol',)

    asset_type = 'CURRENCY'

class PriceCandleFactory(DjangoModelFactory):
    class Meta:
        model = models.PriceCandle

    asset = factory.SubFactory(StockFactory)
    interval_minutes = 1440
    start_at = factory.Faker('date_time_this_month', tzinfo=datetime.timezone.utc)
    open_price = factory.Faker('pydecimal', left_digits=10, right_digits=4, positive=True)
    high_price = factory.LazyAttribute(lambda obj: obj.open_price)
    low_price = factory.LazyAttribute(lambda obj: obj.open_price)
    close_price = factory.LazyAttribute(lambda obj: obj.open_price)
    volume = 0
    source = 'SIMULATION'
