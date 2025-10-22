from django.contrib import admin

from apps.wallets.models import Wallet

# Register your models here.
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'currency', 'created_at', 'updated_at')
    search_fields = ('user__username',)

