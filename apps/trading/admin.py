from django.contrib import admin
from apps.trading.models import Portfolio, Order, Fill, CommissionRule

admin.site.register(Portfolio)
admin.site.register(Order)
admin.site.register(Fill)
admin.site.register(CommissionRule)
