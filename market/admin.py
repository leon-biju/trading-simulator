# mypy: disable-error-code=type-arg

from django.contrib import admin
from market.models import (
    Asset,
    Currency,
    Exchange,
    FXRate,
    PriceCandle,
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
    list_display = ("ticker", "name", "asset_type", "exchange", "currency", "is_active")
    list_filter = ("asset_type", "is_active", "currency")
    search_fields = ("ticker", "name")

@admin.register(FXRate)
class FXRateAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "target_currency", "rate", "last_updated")
    list_filter = ("base_currency", "target_currency")
    search_fields = ("base_currency__code", "target_currency__code")

@admin.register(PriceCandle)
class PriceCandleAdmin(admin.ModelAdmin):
    list_display = ("asset", "interval_minutes", "start_at", "close_price", "source")
    list_filter = ("asset__asset_type", "interval_minutes", "source")
    search_fields = ("asset__name", "asset__ticker")
    raw_id_fields = ("asset",)