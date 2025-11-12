from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from apps.market.models import Exchange, Stock, Currency, CurrencyPair, PriceHistory
from datetime import time, timedelta
import random

class Command(BaseCommand):
    help = 'Seed market data for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding market data...')

        # Clean up existing data to prevent duplicates on re-runs
        PriceHistory.objects.all().delete()
        CurrencyPair.objects.all().delete()
        Stock.objects.all().delete()
        Currency.objects.all().delete()
        Exchange.objects.all().delete()
        self.stdout.write('  Cleared existing market data.')

        # 1. Create Currencies
        currencies = {
            'USD': Currency.objects.create(code='USD', name='United States Dollar'),
            'GBP': Currency.objects.create(code='GBP', name='British Pound Sterling'),
            'EUR': Currency.objects.create(code='EUR', name='Euro'),
        }
        self.stdout.write(f'  Created {len(currencies)} currencies.')

        # 2. Create Exchanges
        lse, _ = Exchange.objects.get_or_create(
            code='LSE',
            defaults={
                'name': 'London Stock Exchange', 
                'timezone': 'Europe/London',
                'open_time': time(8, 0),
                'close_time': time(16, 30)
            }
        )
        nyse, _ = Exchange.objects.get_or_create(
            code='NYSE',
            defaults={
                'name': 'New York Stock Exchange', 
                'timezone': 'America/New_York',
                'open_time': time(9, 30),
                'close_time': time(16, 0)
            }
        )
        nasdaq, _ = Exchange.objects.get_or_create(
            code='NASDAQ',
            defaults={
                'name': 'NASDAQ', 
                'timezone': 'America/New_York',
                'open_time': time(9, 30),
                'close_time': time(16, 0)
            }
        )
        self.stdout.write('  Created 3 exchanges.')

        # 3. Create Stocks and their Price History
        stocks_data = [
            ('VOD.L', 'Vodafone Group plc', currencies['GBP'], lse, '86.48'),
            ('BP.L', 'BP plc', currencies['GBP'], lse, '485.0'),
            ('HSBA.L', 'HSBC Holdings plc', currencies['GBP'], lse, '642.0'),
            ('AAPL', 'Apple Inc', currencies['USD'], nasdaq, '185.50'),
            ('MSFT', 'Microsoft Corporation', currencies['USD'], nasdaq, '398.75'),
            ('GOOGL', 'Alphabet Inc', currencies['USD'], nasdaq, '142.30'),
            ('SPY', 'SPDR S&P 500 ETF', currencies['USD'], nyse, '478.25'),
            ('QQQ', 'Invesco QQQ Trust', currencies['USD'], nasdaq, '412.50'),
        ]
        
        for symbol, name, currency, exchange, price in stocks_data:
            stock = Stock.objects.create(
                symbol=symbol,
                name=name,
                currency=currency,
                exchange=exchange,
                is_active=True
            )
            self.stdout.write(f'    Created stock: {symbol}')
            
            # Create price history for the stock
            self._create_price_history(stock, Decimal(price))

        self.stdout.write(f'  Created {len(stocks_data)} stocks with price history.')

        # 4. Create Currency Pairs and their Price History (FX Rates)
        currency_pairs_data = [
            (currencies['EUR'], currencies['USD'], '1.08'),
            (currencies['GBP'], currencies['USD'], '1.25'),
            (currencies['EUR'], currencies['GBP'], '0.86'),
        ]

        for base_currency, quote_currency, price in currency_pairs_data:
            pair = CurrencyPair.objects.create(
                base_currency=base_currency,
                quote_currency=quote_currency,
                is_active=True
            )
            self.stdout.write(f'    Created currency pair: {pair.symbol}')

            # Create price history for the currency pair
            self._create_price_history(pair, Decimal(price))
        
        self.stdout.write(f'  Created {len(currency_pairs_data)} currency pairs with FX rates.')
        self.stdout.write(self.style.SUCCESS('Market data seeded successfully!'))

    def _create_price_history(self, asset, base_price):
        """Helper to create 30 days of simulated price history for an asset."""
        price_history_batch = []
        for days_ago in range(30, 0, -1):
            timestamp = timezone.now() - timedelta(days=days_ago)
            
            # Simulate some price movement
            variance = Decimal(random.uniform(-0.05, 0.05))
            price = base_price * (1 + variance)
            
            price_history_batch.append(
                PriceHistory(
                    asset=asset,
                    timestamp=timestamp,
                    price=price.quantize(Decimal('0.0001')),
                    source='SIMULATION'
                )
            )
        
        PriceHistory.objects.bulk_create(price_history_batch)
        self.stdout.write(f'      Generated 30 days of price history for {asset.symbol}')