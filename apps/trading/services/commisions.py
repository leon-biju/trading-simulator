from decimal import Decimal, ROUND_HALF_UP
from apps.trading.models import CommissionRule


def calculate(price, quantity, currency) -> Decimal:
    # Calculate commission for a fill

    rule = CommissionRule.objects.filter(currency=currency, active=True).first()

    if not rule:
        return Decimal('0.00')
    
    gross_amt = price * quantity
    commission = ((gross_amt * rule.rate_bps) / Decimal('10000.00')).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP
    )

    if commission < rule.min_fee:
        commission = rule.min_fee

    if rule.max_fee and commission > rule.max_fee:
        commission = rule.max_fee

    return commission