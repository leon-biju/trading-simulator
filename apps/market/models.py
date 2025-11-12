from django.db import models
from django.utils import timezone
import pytz

class Exchange(models.Model):
    """
    Represents a financial exchange where assets are traded.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True) # e.g., 'NYSE', 'NASDAQ'
    country = models.CharField(max_length=50)
    timezone = models.CharField(max_length=50, choices=[(tz, tz) for tz in pytz.all_timezones]) # e.g., 'America/New_York'
    
    open_time = models.TimeField()  # Daily opening time
    close_time = models.TimeField() # Daily closing time

    def is_open(self):
        """
        Check if the exchange is open now.
        """

        # Get the current time in UTC
        utc_now = timezone.now()
        
        # Convert the current time to the exchange's local timezone
        exchange_tz = pytz.timezone(self.time_zone)
        local_time_now = utc_now.astimezone(exchange_tz)
        
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
    ASSET_TYPE_CHOICES = [
        ('STOCK', 'Stock'),
        ('CRYPTO', 'Cryptocurrency'),
        ('CURRENCY', 'Fiat Currency'),
    ]
    
    asset_type = models.CharField(max_length=10, choices=ASSET_TYPE_CHOICES)
    symbol = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3) # The currency the asset is priced in (e.g., 'USD' for AAPL)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE, related_name='assets')
    
    is_active = models.BooleanField(default=True) # To enable/disable trading for an asset

    def __str__(self):
        return f"{self.name} ({self.symbol}) on {self.exchange.code}"


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