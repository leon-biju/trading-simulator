from django.conf import settings
from django.db import models

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=settings.STARTING_BALANCE)
    currency = models.CharField(max_length=10, default='GBP') # We dont ask user yet but here for futureproofing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance} {self.currency}"


class CashTransaction(models.Model):
    class Source(models.TextChoices):
        DEPOSIT = 'DEPOSIT'
        WITHDRAWAL = 'WITHDRAWAL'
        BUY = 'BUY'
        SELL = 'SELL'

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=20, decimal_places=2) # Positive for deposits/buys, negative for withdrawals/sells
    balance_after = models.DecimalField(max_digits=20, decimal_places=2)
    source = models.CharField(max_length=10, choices=Source.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.wallet.user.username}:  {self.amount} ({self.source}) on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"