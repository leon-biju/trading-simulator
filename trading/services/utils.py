"""
Trading utility functions and constants.
"""
from decimal import Decimal, ROUND_HALF_UP


# Fee percentage for trades (0.1%) TODO: Make configurable
TRADING_FEE_PERCENTAGE = Decimal('0.001')


def round_to_two_dp(value: Decimal) -> Decimal:
    """Round decimal to 2 decimal places."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def round_to_eight_dp(value: Decimal) -> Decimal:
    """Round decimal to 8 decimal places (for quantities)."""
    return value.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)
