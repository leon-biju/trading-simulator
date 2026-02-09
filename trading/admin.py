from django.contrib import admin
from trading.models import PortfolioSnapshot

@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin): # type:  ignore[type-arg]
    list_display = ("user", "date", "total_value", "total_cost", "cash_balance")
    list_filter = ("date",)
    search_fields = ("user__username",)
    raw_id_fields = ("user",)