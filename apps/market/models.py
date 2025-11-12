from django.db import models
from django.utils import timezone
from zoneinfo import ZoneInfo, available_timezones

class Exchange(models.Model):
    """
    Represents a financial exchange where assets are traded.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True) # e.g., 'NYSE', 'NASDAQ'
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in available_timezones()]) # e.g., 'America/New_York'
    
    open_time = models.TimeField()  # Daily opening time
    close_time = models.TimeField() # Daily closing time

    def is_currently_open(self):
        """
        Check if the exchange is open now.
        """

        # Get the current time in UTC
        utc_now = timezone.now()
        
        # Convert the current time to the exchange's local timezone
        try:
            if self.timezone not in available_timezones():
                return False  #Invalid treat as closed
            exchange_tz = ZoneInfo(self.timezone)
            local_time_now = utc_now.astimezone(exchange_tz)
        except Exception:
            return False  # If timezone conversion fails, treat as closed
        
        # Check if today is a weekday and the time is within trading hours
        # TODO: Add holiday checks
        is_weekday = local_time_now.weekday() < 5 # Monday=0, Sunday=6
        
        is_trading_hours = self.open_time <= local_time_now.time() <= self.close_time
        
        return is_weekday and is_trading_hours

    def __str__(self):
        return f"{self.name} ({self.code})"


class Asset(models.Model):
    """
    Represents a tradable asset, like a stock or currency pair.
    """
    
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    currency = models.ForeignKey('Currency', on_delete=models.PROTECT) # The currency the asset is priced in
    
    is_active = models.BooleanField(default=True) # To enable/disable trading for an asset

    
class Stock(Asset):
    """
    Represents a stock asset.
    """
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, related_name='assets')

    def __str__(self):
        return f"{self.name} ({self.symbol}) on {self.exchange.code}"


class Currency(models.Model):
    """
    Represents a currency.
    """
    code = models.CharField(max_length=3, unique=True)  # e.g., 'USD', 'EUR'
    name = models.CharField(max_length=50)              # e.g., 'United States Dollar'

    def __str__(self):
        return f"{self.name} ({self.code})"


class CurrencyPair(Asset):
    """
    Represents a currency pair asset (e.g., EUR/USD).
    """
    base_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='base_currency_pairs')  # e.g., 'EUR'
    quote_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='quote_currency_pairs') # e.g., 'USD'

    def save(self, *args, **kwargs):
        # Auto-generate symbol and name if not provided
        if not self.symbol:
            self.symbol = f"{self.base_currency.code}{self.quote_currency.code}"
        if not self.name:
            self.name = f"{self.base_currency.name}/{self.quote_currency.name}"

        self.currency = self.quote_currency 
        super().save(*args, **kwargs)


class PriceHistory(models.Model):
    """
    Stores timestamped price data for assets.
    """
    SOURCE_CHOICES = [
        ('SIMULATION', 'Simulated Data'),
        ('LIVE', 'Live API Data'),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='price_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=19, decimal_places=4)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)

    class Meta:
        unique_together = ['asset', 'timestamp']
        get_latest_by = 'timestamp'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['asset', 'timestamp', 'source']),
        ]