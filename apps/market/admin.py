from django.contrib import admin
from apps.market.models import Exchange, Stock, Currency, CurrencyPair, PriceHistory

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'timezone', 'open_time', 'close_time')
    search_fields = ('name', 'code')

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'exchange', 'currency', 'is_active')
    list_filter = ('is_active', 'exchange', 'currency')
    search_fields = ('name', 'symbol')

@admin.register(CurrencyPair)
class CurrencyPairAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'base_currency', 'quote_currency', 'is_active')
    list_filter = ('is_active', 'base_currency', 'quote_currency')
    search_fields = ('name', 'symbol')
    readonly_fields = ('symbol', 'name')

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('asset', 'timestamp', 'price', 'source')
    list_filter = ('asset', 'source')
    search_fields = ('asset__name', 'asset__symbol')