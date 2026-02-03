from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction

from ..models import Currency, FXRate


def round_to_two_dp(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)


@transaction.atomic
def update_currency_prices(currency_update_dict: dict[str, Any]) -> int:
    quotes = currency_update_dict.get("quotes", {})
    timestamp = currency_update_dict.get("timestamp")
    if timestamp is None:
        raise ValueError("Missing timestamp in payload")

    base_currency = Currency.objects.get(is_base=True)
    base_currency_code = base_currency.code

    currency_codes = Currency.objects.exclude(is_base=True).values_list("code", flat=True)
    updated = 0
    for currency_code in currency_codes:
        quote_key = f"{base_currency_code}{currency_code}"
        price_str = quotes.get(quote_key)
        if price_str is None:
            continue

        try:
            price = Decimal(price_str).quantize(Decimal("0.000001"))
        except Exception as e:
            raise ValueError(f"Invalid price for {quote_key}: {price_str}") from e

        FXRate.objects.update_or_create(
            base_currency=base_currency,
            target_currency=Currency.objects.get(code=currency_code),
            defaults={"rate": price},
        )
        updated += 1

    return updated


def get_fx_rate(from_currency_code: str, to_currency_code: str) -> Decimal | None:
    if from_currency_code == to_currency_code:
        return Decimal("1.0")

    try:
        from_currency = Currency.objects.get(code=from_currency_code)
    except Currency.DoesNotExist:
        raise LookupError(f"Currency not found: {from_currency_code}")

    try:
        to_currency = Currency.objects.get(code=to_currency_code)
    except Currency.DoesNotExist:
        raise LookupError(f"Currency not found: {to_currency_code}")

    from_rate = FXRate.objects.filter(
        base_currency__is_base=True,
        target_currency=from_currency,
    ).first()

    to_rate = FXRate.objects.filter(
        base_currency__is_base=True,
        target_currency=to_currency,
    ).first()

    if from_rate is None:
        raise LookupError(f"FX rate not found for currency: {from_currency_code}")
    if to_rate is None:
        raise LookupError(f"FX rate not found for currency: {to_currency_code}")

    return to_rate.rate / from_rate.rate


def get_fx_conversion(
    from_currency_code: str,
    to_currency_code: str,
    *,
    from_amount: Decimal | None = None,
    to_amount: Decimal | None = None,
) -> tuple[Decimal, Decimal]:
    if (from_amount is None) == (to_amount is None):
        raise ValueError("Specify exactly one of from_amount or to_amount")

    exchange_rate = get_fx_rate(from_currency_code, to_currency_code)
    if exchange_rate is None:
        raise LookupError(f"Unsupported currency pair: {from_currency_code}{to_currency_code}")

    if from_amount is not None:
        if from_amount <= 0:
            raise ValueError("from_amount must be > 0")
        return from_amount, round_to_two_dp(from_amount * exchange_rate)

    assert to_amount is not None

    if to_amount <= 0:
        raise ValueError("to_amount must be > 0")
    return round_to_two_dp(to_amount / exchange_rate), to_amount
