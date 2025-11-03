from decimal import Decimal
from django.db import models

class Exchange(models.Model):
    code = models.CharField(max_length=10, unique=True) # e.g. NYSE, NASDAQ
    name = models.CharField(max_length=64) # e.g. New York Stock Exchange

    def __str__(self):
        return f"{self.code} ({self.name})"
    
class Instrument(models.Model):
    ticker = models.CharField(max_length=20, db_index=True) # e.g. AAPL, BTCUSD
    name = models.CharField(max_length=200) # e.g. Apple Inc., Bitcoin to US Dollar
    currency = models.CharField(max_length=3)  # e.g. USD, EUR
    exchange = models.ForeignKey(Exchange, null=True, on_delete=models.SET_NULL)
    tick_size = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('0.01')) # Minimum price movement
    lot_size = models.IntegerField(default=1) # Minimum tradeable quantity
    active = models.BooleanField(default=True) # Is this instrument currently active for trading

    class Meta:
        unique_together = ('ticker', 'exchange')
        indexes = [models.Index(fields=['currency', 'active'])]

    def __str__(self):
        return f"{self.ticker} on {self.exchange.code}"


class PriceBar(models.Model):
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE) # e.g. AAPL, BTCUSD
    period_start = models.DateTimeField() # Start time of the period
    open = models.DecimalField(max_digits=18, decimal_places=6) # Opening price
    high = models.DecimalField(max_digits=18, decimal_places=6) # Highest price
    low = models.DecimalField(max_digits=18, decimal_places=6) # Lowest price
    close = models.DecimalField(max_digits=18, decimal_places=6) # Closing price
    volume = models.BigIntegerField() # Volume traded during the period

    class Meta:
        unique_together = [['instrument', 'period_start']]
        indexes = [models.Index(fields=['instrument', '-period_start'])]


class Quote(models.Model):
    instrument = models.OneToOneField(Instrument, on_delete=models.CASCADE) # e.g. AAPL, BTCUSD
    last_price = models.DecimalField(max_digits=18, decimal_places=6) # Last traded price
    bid = models.DecimalField(max_digits=18, decimal_places=6, null=True) # Current highest bid price
    ask = models.DecimalField(max_digits=18, decimal_places=6, null=True) # Current lowest ask price
    timestamp = models.DateTimeField(db_index=True) # Timestamp of the quote
    updated_at = models.DateTimeField(auto_now=True) # Last updated time

class FxRate(models.Model):
    base_currency = models.CharField(max_length=3) # e.g. USD, EUR
    quote_currency = models.CharField(max_length=3) # e.g. JPY, GBP
    rate = models.DecimalField(max_digits=18, decimal_places=8) # Exchange rate 
    timestamp = models.DateTimeField(db_index=True) # Time of the rate quote

    class Meta:
        unique_together = [['base_currency', 'quote_currency', 'timestamp']]
        indexes = [models.Index(fields=['base_currency', 'quote_currency', '-timestamp'])]

    def __str__(self):
        return f"1 {self.base_currency} = {self.rate} {self.quote_currency} as of {self.timestamp}"
