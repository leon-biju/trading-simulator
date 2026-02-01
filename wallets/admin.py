# mypy: disable-error-code=type-arg
from django.contrib import admin

from wallets.models import Wallet

# Register your models here.
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'available_balance', 'currency', 'created_at', 'updated_at')
    search_fields = ('user__username',)

