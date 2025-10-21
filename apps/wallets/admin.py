from django.contrib import admin

from apps.wallets.models import Wallet

# Register your models here.
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency_code', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    def currency_code(self, obj):
        return obj.currency.upper()
