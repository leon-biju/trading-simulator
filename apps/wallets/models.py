from django.conf import settings
from django.db import models

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=settings.STARTING_BALANCE)
    currency = models.CharField(max_length=10, default='GBP')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet of {self.user.username} - Balance: {self.balance} {self.currency}"


class CashTransaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.enums.Choices('CASH_IN', 'CASH_OUT')
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    balance_after = models.DecimalField(max_digits=20, decimal_places=2)
    source = models.enums.Choices('DEPOSIT', 'WITHDRAWAL', 'BUY', 'SELL')
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of {self.amount} on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"