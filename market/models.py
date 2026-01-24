from decimal import Decimal
from django.db import models
from django.utils import timezone
from zoneinfo import ZoneInfo, available_timezones

class Exchange(models.Model):
    """
    Represents a financial exchange where stocks are traded.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True) # e.g., 'NYSE', 'NASDAQ'
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in sorted(available_timezones())]) # e.g., 'America/New_York'
    
    open_time = models.TimeField()
    close_time = models.TimeField()

    def is_currently_open(self) -> bool:

        utc_now = timezone.now()
        
        # Convert the current time to the exchange's local timezone
        try:
            exchange_tz = ZoneInfo(self.timezone)
            local_time_now = utc_now.astimezone(exchange_tz)
        except Exception:
            # If timezone conversion fails, assume closed
            return False
        
        # Check if today is a weekday and the time is within trading hours
        # TODO: Add holiday checks
        is_weekday = local_time_now.weekday() < 5 # Monday=0, Sunday=6
        
        is_trading_hours = self.open_time <= local_time_now.time() <= self.close_time
        
        return is_weekday and is_trading_hours

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


#TODO: Add a symbol to represent currency symbols once other migrations done
class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)  # e.g., 'USD', 'EUR'
    name = models.CharField(max_length=50)              # e.g., 'United States Dollar'
    is_base = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs): # type: ignore[no-untyped-def]
        if self.is_base:
            Currency.objects.filter(is_base=True).exclude(pk=self.pk).update(is_base=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.code
    
    class Meta:
        verbose_name_plural = "currencies"


class Asset(models.Model):
    """
    Represents a tradable asset, like a stock or a currency.
    """
    ASSET_TYPE_CHOICES = [
        ('STOCK', 'Stock'),
        ('CURRENCY', 'Currency'),
    ]

    asset_type = models.CharField(max_length=10, choices=ASSET_TYPE_CHOICES)
    #TODO: Rename to 'ticker' once other migrations are done
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT) # The currency the asset is priced in. for currency assets it's the base currency
    
    is_active = models.BooleanField(default=True) # To enable/disable trading for an asset

    def get_latest_price(self) -> Decimal | None:
        latest_price_entry = PriceHistory.objects.filter(
            asset=self
        ).order_by("-timestamp").first()
        
        if latest_price_entry is None:
            return None
        
        return latest_price_entry.price

    
class Stock(Asset):
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, related_name='stocks')

    def __str__(self) -> str:
        return f"{self.name} ({self.symbol}) on {self.exchange.code}"


class CurrencyAsset(Asset):

    def __str__(self) -> str:
        return f"{self.name} ({self.symbol})"


class PriceHistory(models.Model):
    """
    Stores timestamped price data for assets.
    """
    SOURCE_CHOICES = [
        ('SIMULATION', 'Simulated Data'),
        ('LIVE', 'Live API Data'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='price_history')
    timestamp = models.DateTimeField(default=timezone.now)
    price = models.DecimalField(max_digits=19, decimal_places=4)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)

    class Meta:
        unique_together = ['asset', 'timestamp']
        get_latest_by = 'timestamp'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['asset', 'timestamp', 'source']),
        ]

class DailyPriceHistory(models.Model):
    """
    Stores daily aggregated price data for assets.
    """
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='daily_price_history')
    date = models.DateField()
    open_price = models.DecimalField(max_digits=19, decimal_places=4)
    high_price = models.DecimalField(max_digits=19, decimal_places=4)
    low_price = models.DecimalField(max_digits=19, decimal_places=4)
    close_price = models.DecimalField(max_digits=19, decimal_places=4)
    volume = models.BigIntegerField()
    source = models.CharField(max_length=10, choices=PriceHistory.SOURCE_CHOICES)

    class Meta:
        unique_together = ['asset', 'date']
        get_latest_by = 'date'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['asset', 'date', 'source']),
        ]