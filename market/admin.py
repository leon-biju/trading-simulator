# mypy: disable-error-code=type-arg

from django.contrib import admin
from market.models import (
    Asset,
    Currency,
    CurrencyAsset,
    Exchange,
    PriceCandle,
    Stock,
)

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "timezone", "open_time", "close_time")
    search_fields = ("name", "code")

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_base")
    search_fields = ("name", "code")
    list_filter = ("is_base",)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "asset_type", "currency", "is_active")
    list_filter = ("asset_type", "is_active", "currency")
    search_fields = ("symbol", "name")

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("name", "symbol", "exchange", "currency", "is_active")
    list_filter = ("is_active", "exchange", "currency")
    search_fields = ("name", "symbol")

@admin.register(CurrencyAsset)
class CurrencyAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "symbol", "currency", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "symbol")

@admin.register(PriceCandle)
class PriceCandleAdmin(admin.ModelAdmin):
    list_display = ("asset", "interval_minutes", "start_at", "close_price", "source")
    list_filter = ("asset__asset_type", "interval_minutes", "source")
    search_fields = ("asset__name", "asset__symbol")
    raw_id_fields = ("asset",)