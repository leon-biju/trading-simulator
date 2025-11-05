from django.contrib import admin
from .models import Exchange, Instrument, PriceBar, Quote, FxRate

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['ticker', 'name', 'currency', 'exchange', 'active', 'tick_size', 'lot_size']
    list_filter = ['currency', 'active', 'exchange']
    search_fields = ['ticker', 'name']

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['instrument', 'last_price', 'bid', 'ask', 'timestamp']
    list_filter = ['timestamp']
    readonly_fields = ['updated_at']

@admin.register(PriceBar)
class PriceBarAdmin(admin.ModelAdmin):
    list_display = ['instrument', 'period_start', 'open', 'high', 'low', 'close', 'volume']
    list_filter = ['instrument', 'period_start']
    date_hierarchy = 'period_start'

@admin.register(FxRate)
class FxRateAdmin(admin.ModelAdmin):
    list_display = ['base_currency', 'quote_currency', 'rate', 'timestamp']
    list_filter = ['base_currency', 'quote_currency']