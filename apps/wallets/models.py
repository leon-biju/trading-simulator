from django.conf import settings
from django.db import models

class Currency(models.TextChoices):
    GBP = 'GBP'
    USD = 'USD'
    EUR = 'EUR'
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

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance} {self.currency}"


class Transaction(models.Model):
    class Source(models.TextChoices):
        DEPOSIT = 'DEPOSIT'
        WITHDRAWAL = 'WITHDRAWAL'
        BUY = 'BUY'
        SELL = 'SELL'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=20, decimal_places=2) # Positive for deposits/buys, negative for withdrawals/sells
    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.GBP)
    balance_after = models.DecimalField(max_digits=20, decimal_places=2)
    source = models.CharField(max_length=10, choices=Source.choices)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.wallet.user.username}:  {self.amount} {self.currency} ({self.source}) on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"