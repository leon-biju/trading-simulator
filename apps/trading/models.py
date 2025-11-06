from django.db import models
from decimal import Decimal
from django.conf import settings
from apps.wallets.models import Wallet
from apps.market.models import Instrument

class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    base_currency = models.CharField(max_length=3)
    default_wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'base_currency']]


class Order(models.Model):
    class Side(models.TextChoices):
        BUY = 'BUY'
        SELL = 'SELL'

    class Type(models.TextChoices):
        MARKET = 'MARKET'
        LIMIT = 'LIMIT'

    class Status(models.TextChoices):
        PENDING = 'PENDING'
        OPEN = 'OPEN'
        FILLED = 'FILLED'
        CANCELLED = 'CANCELLED'
        REJECTED = 'REJECTED'

    class TimeInForce(models.TextChoices):
        DAY = 'DAY'
        GTC = 'GTC'
        IOC = 'IOC'

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT)
    side = models.CharField(max_length=4, choices=Side.choices)
    order_type = models.CharField(max_length=10, choices=Type.choices)
    quantity = models.IntegerField()
    limit_price = models.DecimalField(max_digits=18, decimal_places=6, null=True)
    time_in_force = models.CharField(max_length=3, choices=TimeInForce.choices, default=TimeInForce.DAY)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reject_reason = models.TextField(null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['portfolio', 'status', '-submitted_at'])]


class Fill(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='fills')
    filled_at = models.DateTimeField(auto_now_add=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=18, decimal_places=6)
    commission = models.DecimalField(max_digits=18, decimal_places=6)
    total_cost = models.DecimalField(max_digits=18, decimal_places=6)  # signed

    class Meta:
        indexes = [models.Index(fields=['order', 'filled_at'])]


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    avg_cost = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('0'))
    realized_pnl = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal('0'))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['portfolio', 'instrument']]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name='quantity_non_negative')
        ]


class CommissionRule(models.Model):
    name = models.CharField(max_length=100)
    rate_bps = models.DecimalField(max_digits=6, decimal_places=2)  # basis points
    min_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    currency = models.CharField(max_length=3)
    active = models.BooleanField(default=True)