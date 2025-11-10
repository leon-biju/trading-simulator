from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from apps.market.models import Exchange, Asset, PriceHistory
from datetime import timedelta

# seed market data to help development
class Command(BaseCommand):
    help = 'Seed market data for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding market data...')
        
        # create exchanges
        lse, _ = Exchange.objects.get_or_create(
            code='LSE',
            defaults={'name': 'London Stock Exchange', 'country': 'UK', 'timezone': 'Europe/London'}
        )
        nyse, _ = Exchange.objects.get_or_create(
            code='NYSE',
            defaults={'name': 'New York Stock Exchange', 'country': 'USA', 'timezone': 'America/New_York'}
        )
        nasdaq, _ = Exchange.objects.get_or_create(
            code='NASDAQ',
            defaults={'name': 'NASDAQ', 'country': 'USA', 'timezone': 'America/New_York'}
        )
        
        # create assets and price history

        assets_data = [
            ('VOD.L', 'Vodafone Group plc', 'GBP', lse, '86.48'),
            ('BP.L', 'BP plc', 'GBP', lse, '485.0'),
            ('HSBA.L', 'HSBC Holdings plc', 'GBP', lse, '642.0'),
            ('AAPL', 'Apple Inc', 'USD', nasdaq, '185.50'),
            ('MSFT', 'Microsoft Corporation', 'USD', nasdaq, '398.75'),
            ('GOOGL', 'Alphabet Inc', 'USD', nasdaq, '142.30'),
            ('SPY', 'SPDR S&P 500 ETF', 'USD', nyse, '478.25'),
            ('QQQ', 'Invesco QQQ Trust', 'USD', nasdaq, '412.50'),
        ]
        
        assets = {}
        for symbol, name, ccy, exch, price in assets_data:

            # Create asset
            asset, created = Asset.objects.get_or_create(
                symbol=symbol,
                defaults={
                    'name': name,
                    'asset_type': 'STOCK',
                    'currency': ccy,
                    'exchange': exch,
                    'is_active': True
                }
            )
            assets[symbol] = asset
            
            # Create some historical price bars (last 30 days)
            base_price = Decimal(price)
            for days_ago in range(30, 0, -1):
                date = timezone.now() - timedelta(days=days_ago)
                
                # Simulate some price movement
                variance = Decimal(str((hash(f"{symbol}{days_ago}") % 100) / 1000))  # -0.05 to +0.05
                open_price = base_price * (1 + variance - Decimal('0.025'))
                close_price = base_price * (1 + variance + Decimal('0.025'))
                high_price = max(open_price, close_price) * Decimal('1.01')
                low_price = min(open_price, close_price) * Decimal('0.99')
                
                PriceHistory.objects.get_or_create(
                    asset=asset,
                    timestamp=date.replace(hour=9, minute=0, second=0, microsecond=0),
                    defaults={
                        'open': open_price.quantize(Decimal('0.01')),
                        'high': high_price.quantize(Decimal('0.01')),
                        'low': low_price.quantize(Decimal('0.01')),
                        'close': close_price.quantize(Decimal('0.01')),
                        'volume': 1000000 + (days_ago * 10000)
                    }
                )
            
            if created:
                self.stdout.write(f'  Created asset: {symbol}')
        
        self.stdout.write(self.style.SUCCESS('Market data seeded successfully!'))