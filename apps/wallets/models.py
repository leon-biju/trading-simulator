from django.conf import settings
from django.db import models
from .constants import CURRENCY_SYMBOLS

class Currency(models.TextChoices):
    GBP = 'GBP', 'GBP'
    USD = 'USD', 'USD'
    EUR = 'EUR', 'EUR'
    # Additional currencies can be added here later

class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)

    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.GBP)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One user gets one wallet for a given currency
        constraints = [
            models.UniqueConstraint(fields=['user', 'currency'], name='unique_user_currency_wallet')
        ]

    @property
    def symbol(self) -> str:
        return CURRENCY_SYMBOLS.get(self.currency, self.currency)
    
    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance} {self.currency}"


class Transaction(models.Model):
    class Source(models.TextChoices):
        DEPOSIT = 'DEPOSIT'
        WITHDRAWAL = 'WITHDRAWAL'
        BUY = 'BUY'
        SELL = 'SELL'
        FX_TRANSFER = 'FX_TRANSFER', 'FX_TRANSFER'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=20, decimal_places=2) # Positive for deposits/buys, negative for withdrawals/sells
    balance_after = models.DecimalField(max_digits=20, decimal_places=2)
    source = models.CharField(max_length=16, choices=Source.choices)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.wallet.user.username}:  {self.amount} {self.currency} ({self.source}) on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    


# Transfer between wallets of same user but different currencies
class Fx_Transfer(models.Model):
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='fx_transfers_from')
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='fx_transfers_to')
    from_amount = models.DecimalField(max_digits=20, decimal_places=2)
    to_amount = models.DecimalField(max_digits=20, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FX Transfer: [{self.from_wallet.currency}] to [{self.to_wallet.currency}] - {self.from_wallet.symbol}{self.to_amount} at {self.exchange_rate} on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"