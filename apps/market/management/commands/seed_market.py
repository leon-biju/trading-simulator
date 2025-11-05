from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from apps.market.models import Exchange, Instrument, Quote, PriceBar, FxRate
from datetime import timedelta

# seed market data to help development
class Command(BaseCommand):
    help = 'Seed market data for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding market data...')
        
        # create exchanges
        lse, _ = Exchange.objects.get_or_create(
            code='LSE',
            defaults={'name': 'London Stock Exchange'}
        )
        nyse, _ = Exchange.objects.get_or_create(
            code='NYSE',
            defaults={'name': 'New York Stock Exchange'}
        )
        nasdaq, _ = Exchange.objects.get_or_create(
            code='NASDAQ',
            defaults={'name': 'NASDAQ'}
        )
        
        # create instruments with quotes and price bars

        instruments_data = [
            ('VOD.L', 'Vodafone Group plc', 'GBX', lse, '86.48', '0.01', 1),
            ('BP.L', 'BP plc', 'GBX', lse, '485.0', '0.1', 1),
            ('HSBA.L', 'HSBC Holdings plc', 'GBX', lse, '642.0', '0.1', 1),
            ('AAPL', 'Apple Inc', 'USD', nasdaq, '185.50', '0.01', 1),
            ('MSFT', 'Microsoft Corporation', 'USD', nasdaq, '398.75', '0.01', 1),
            ('GOOGL', 'Alphabet Inc', 'USD', nasdaq, '142.30', '0.01', 1),
            ('SPY', 'SPDR S&P 500 ETF', 'USD', nyse, '478.25', '0.01', 1),
            ('QQQ', 'Invesco QQQ Trust', 'USD', nasdaq, '412.50', '0.01', 1),
        ]
        
        instruments = {}
        for ticker, name, ccy, exch, price, tick, lot in instruments_data:

            # Create instrument
            inst, created = Instrument.objects.get_or_create(
                ticker=ticker,
                defaults={
                    'name': name,
                    'currency': ccy,
                    'exchange': exch,
                    'tick_size': Decimal(tick),
                    'lot_size': lot,
                    'active': True
                }
            )
            instruments[ticker] = inst
            
            # Create quote
            Quote.objects.update_or_create(
                instrument=inst,
                defaults={
                    'last_price': Decimal(price),
                    'bid': Decimal(price) - Decimal('0.01'),
                    'ask': Decimal(price) + Decimal('0.01'),
                    'timestamp': timezone.now()
                }
            )
            
            # Create some historical price bars (last 30 days)
            base_price = Decimal(price)
            for days_ago in range(30, 0, -1):
                date = timezone.now() - timedelta(days=days_ago)
                
                # Simulate some price movement
                variance = Decimal(str((hash(f"{ticker}{days_ago}") % 100) / 1000))  # -0.05 to +0.05
                open_price = base_price * (1 + variance - Decimal('0.025'))
                close_price = base_price * (1 + variance + Decimal('0.025'))
                high_price = max(open_price, close_price) * Decimal('1.01')
                low_price = min(open_price, close_price) * Decimal('0.99')
                
                PriceBar.objects.get_or_create(
                    instrument=inst,
                    period_start=date.replace(hour=9, minute=0, second=0, microsecond=0),
                    defaults={
                        'open': open_price.quantize(Decimal('0.01')),
                        'high': high_price.quantize(Decimal('0.01')),
                        'low': low_price.quantize(Decimal('0.01')),
                        'close': close_price.quantize(Decimal('0.01')),
                        'volume': 1000000 + (days_ago * 10000)
                    }
                )
            
            if created:
                self.stdout.write(f'  Created instrument: {ticker}')
        
        # FX Rates
        fx_data = [
            ('GBP', 'USD', '1.30000000'),
            ('USD', 'GBP', '0.76923077'),
            ('GBP', 'EUR', '1.17000000'),
            ('EUR', 'GBP', '0.85470085'),
            ('USD', 'EUR', '0.90000000'),
            ('EUR', 'USD', '1.11111111'),
        ]
        
        for base, quote, rate in fx_data:
            FxRate.objects.get_or_create(
                base_currency=base,
                quote_currency=quote,
                timestamp=timezone.now(),
                defaults={'rate': Decimal(rate)}
            )
            self.stdout.write(f'  Created FX rate: {base}/{quote} = {rate}')
        
        self.stdout.write(self.style.SUCCESS('Market data seeded successfully!'))