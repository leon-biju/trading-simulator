from django.core.management.base import BaseCommand
from decimal import Decimal
from trading.models import CommissionRule

class Command(BaseCommand):
    help = 'Seed trading configuration data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding trading data...')
        
        # Commission Rules
        rules = [
            ('UK Equities', 'GBP', '10.00', '1.00', None),
            ('US Equities', 'USD', '10.00', '1.00', None),
            ('EU Equities', 'EUR', '10.00', '1.00', None),
        ]
        
        for name, ccy, rate, min_fee, max_fee in rules:
            rule, created = CommissionRule.objects.get_or_create(
                name=name,
                currency=ccy,
                defaults={
                    'rate_bps': Decimal(rate),
                    'min_fee': Decimal(min_fee) if min_fee else None,
                    'max_fee': Decimal(max_fee) if max_fee else None,
                    'active': True
                }
            )
            if created:
                self.stdout.write(f'  Created commission rule: {name}')
        
        self.stdout.write(self.style.SUCCESS('Trading data seeded successfully!'))

