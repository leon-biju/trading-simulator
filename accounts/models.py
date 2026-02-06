from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from market.models import Currency
from market.services.fx import get_fx_conversion

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    @property
    def total_cash(self) -> Decimal:
        """
        Calculate the total cash value across all wallets for the user, converted to base currency
        """
        wallets = self.wallet_set.all().select_related('currency')
        total = Decimal('0')
        base_currency = Currency.objects.filter(is_base=True).first()
        if base_currency:
            for wallet in wallets:
                total += get_fx_conversion(
                    from_currency_code=wallet.currency.code,
                    to_currency_code=base_currency.code,
                    from_amount=wallet.balance,
                    to_amount=None
                )[1]  # For to_amount
        return total


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    display_name = models.CharField(max_length=100, blank=True)
    preferences_json = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Profile of {self.user.username}"