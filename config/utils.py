from decimal import Decimal
from typing import Optional

from market.services.fx import get_fx_conversion


def convert_to_home(
    from_currency_code: str,
    home_currency_code: str,
    amount: Optional[Decimal],
) -> Optional[Decimal]:
    """Convert an amount from an asset's native currency to the user's home currency."""
    if amount is None:
        return None
    if from_currency_code == home_currency_code:
        return amount
    _, converted = get_fx_conversion(
        from_currency_code=from_currency_code,
        to_currency_code=home_currency_code,
        from_amount=amount,
        to_amount=None,
    )
    return converted
