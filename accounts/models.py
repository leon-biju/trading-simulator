from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from market.models import Asset, Currency
from market.services.fx import get_fx_conversion

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    # These are not auth related but these are here as helpers so easy access straight from request.user object
    @property
    def home_currency(self) -> Currency:
        profile = getattr(self, 'profile', None)
        if profile:
            return profile.home_currency # type: ignore[no-any-return]
        # default to USD if no profile or home currency set (not really possible)
        return Currency.objects.get(code="USD")

    @property
    def total_cash(self) -> Decimal:
        """
        Calculate the total cash value across all wallets for the user, converted to home currency
        """
        wallets = self.wallet_set.all().select_related('currency')
        total = Decimal('0')
        home_currency = self.home_currency
        if home_currency:
            for wallet in wallets:
                total += get_fx_conversion(
                    from_currency_code=wallet.currency.code,
                    to_currency_code=home_currency.code,
                    from_amount=wallet.balance,
                    to_amount=None
                )[1]  # For to_amount
        return total


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    display_name = models.CharField(max_length=100, blank=True)
    preferences_json = models.JSONField(default=dict, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    home_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=False, blank=False)

    def __str__(self) -> str:
        return f"{self.user.username}'s profile"


class PasswordResetOTP(models.Model):
    OTP_EXPIRY_SECONDS = 600  # 10 minutes

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_reset_otps')
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_valid(self) -> bool:
        if self.used:
            return False
        age = (timezone.now() - self.created_at).total_seconds()
        return age <= self.OTP_EXPIRY_SECONDS


class WatchlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='watchlist',
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='watchlisted_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'asset'], name='unique_watchlist_item')
        ]
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.user} watching {self.asset}"