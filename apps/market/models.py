from django.db import models

class Exchange(models.Model):
    """
    Represents a financial exchange where assets are traded.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True) # e.g., 'NYSE', 'NASDAQ'
    country = models.CharField(max_length=50)
    timezone = models.CharField(max_length=50) # e.g., 'America/New_York'
    
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
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='price_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=19, decimal_places=4)

    class Meta:
        unique_together = ['asset', 'timestamp']
        get_latest_by = 'timestamp'
        ordering = ['-timestamp']