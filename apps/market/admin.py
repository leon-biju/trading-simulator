from django.contrib import admin
from apps.market.models import Exchange, Asset, PriceHistory

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'country', 'timezone')
    search_fields = ('name', 'code', 'country')

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'asset_type', 'exchange', 'is_active')
    list_filter = ('asset_type', 'is_active', 'exchange')
    search_fields = ('name', 'symbol')

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('asset', 'timestamp', 'price')
    list_filter = ('asset',)
    search_fields = ('asset__name', 'asset__symbol')