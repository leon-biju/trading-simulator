from django.contrib import admin
from .models import Portfolio, Order, Fill, Position, CommissionRule

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'base_currency', 'default_wallet', 'created_at']
    list_filter = ['base_currency']
    search_fields = ['user__username']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'portfolio', 'instrument', 'side', 'order_type', 'quantity', 'status', 'submitted_at']
    list_filter = ['status', 'side', 'order_type']
    readonly_fields = ['submitted_at', 'updated_at']
    search_fields = ['portfolio__user__username', 'instrument__ticker']

@admin.register(Fill)
class FillAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'quantity', 'price', 'commission', 'total_cost', 'filled_at']
    readonly_fields = ['filled_at']
    search_fields = ['order__id']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['id', 'portfolio', 'instrument', 'quantity', 'avg_cost', 'realized_pnl', 'updated_at']
    list_filter = ['portfolio__user']
    readonly_fields = ['updated_at']
    search_fields = ['instrument__ticker', 'portfolio__user__username']

@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rate_bps', 'min_fee', 'max_fee', 'currency', 'active']
    list_filter = ['currency', 'active']