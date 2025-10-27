from typing import Optional, Tuple
from .models import Fx_Transfer, Transaction, Wallet, Currency
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP

#TODO: Will use market FX rates later
DUMMY_FX_RATES = {
    'GBP': Decimal('1.00'),
    'USD': Decimal('1.25'),
    'EUR': Decimal('1.15'),
}

def round_to_two_dp(value: Decimal) -> Decimal:
    return value.quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)

def create_transaction(
        wallet_id: int, 
        amount: Decimal, 
        source: Transaction.Source, 
        description: str,
    ) -> Tuple[Optional[Transaction], Optional[str]]:
    # Easy error handling for any issues like insufficient funds

    if amount == 0:
        return (None, "ZERO_AMOUNT_TRANSACTION")
    try:
        with transaction.atomic():
            # Prevent race conditions by locking this wallet record
            wallet = Wallet.objects.select_for_update().get(id=wallet_id)

            new_balance = wallet.balance + amount

            if new_balance < 0:
                return (None, "INSUFFICIENT_FUNDS")

            new_transaction = Transaction.objects.create(
                wallet=wallet,
                amount=amount,
                balance_after=round_to_two_dp(new_balance),
                source=source,
                description=description
            )

            wallet.balance = new_balance
            wallet.save(update_fields=['balance', 'updated_at'])

            return (new_transaction, None)
        
    except Wallet.DoesNotExist:
        return (None, "WALLET_DOES_NOT_EXIST")
    except Exception as e:
        return (None, f"UNEXPECTED_ERROR: {str(e)}")
    

def get_fx_conversion(
    from_currency: str,
    to_currency: str,
    from_amount: Optional[Decimal] = None,
    to_amount: Optional[Decimal] = None,
) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
    # Returns (from_amount, to_amount, error)
    if from_currency not in Currency.values or to_currency not in Currency.values:
        return (None, None, "UNSUPPORTED_CURRENCY")

    if (from_amount is None and to_amount is None) or (from_amount is not None and to_amount is not None):
        return (None, None, "SPECIFY_EITHER_FROM_OR_TO_AMOUNT")

    from_rate = DUMMY_FX_RATES.get(from_currency)
    to_rate = DUMMY_FX_RATES.get(to_currency)

    if not from_rate or not to_rate:
        return (None, None, "UNSUPPORTED_CURRENCY_FOR_FX")

    exchange_rate = to_rate / from_rate

    if from_amount is not None:
        if from_amount <= 0:
            return (None, None, "INVALID_FROM_AMOUNT")
        calculated_to_amount = round_to_two_dp(from_amount * exchange_rate)
        return (from_amount, calculated_to_amount, None)
    else: # to_amount is not None
        if to_amount <= 0:
            return (None, None, "INVALID_TO_AMOUNT")
        calculated_from_amount = round_to_two_dp(to_amount / exchange_rate)
        return (calculated_from_amount, to_amount, None)


def perform_fx_transfer(
        user_id: int,
        from_wallet_currency: str,
        to_wallet_currency: str,
        from_amount: Optional[Decimal] = None,
        to_amount: Optional[Decimal] = None,
    ) -> Tuple[Optional[Fx_Transfer], Optional[str]]:
    # Transfer funds between two wallets of the same user but different currencies
    # Specify either from_amount OR to_amount, not both
    if from_wallet_currency == to_wallet_currency:
        return (None, "SAME_WALLET_TRANSFER")

    from_amount, to_amount, error = get_fx_conversion(
        from_currency=from_wallet_currency,
        to_currency=to_wallet_currency,
        from_amount=from_amount,
        to_amount=to_amount
    )

    if error:
        return (None, error)

    try:
        with transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency=from_wallet_currency)
            to_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency=to_wallet_currency)

            if from_wallet.balance < from_amount:
                return (None, "INSUFFICIENT_FUNDS_IN_FROM_WALLET")

            # Get dummy FX rates for exchange rate calculation
            from_rate = DUMMY_FX_RATES.get(from_wallet.currency)
            to_rate = DUMMY_FX_RATES.get(to_wallet.currency)
            exchange_rate = to_rate / from_rate

            _, from_error = create_transaction(
                wallet_id=from_wallet.id,
                amount=-from_amount,
                source=Transaction.Source.FX_TRANSFER,
                description=f"FX Transfer of {to_wallet.symbol}{to_amount:.2f} ({from_wallet.symbol}{from_amount:.2f}) to {to_wallet.currency} wallet"
            )
            if from_error:
                return (None, from_error)

            _, to_error = create_transaction(
                wallet_id=to_wallet.id,
                amount=to_amount,
                source=Transaction.Source.FX_TRANSFER,
                description=f"FX Transfer of {to_wallet.symbol}{to_amount:.2f} ({from_wallet.symbol}{from_amount:.2f}) from {from_wallet.currency} wallet"
            )
            if to_error:
                return (None, to_error)

            fx_transfer = Fx_Transfer.objects.create(
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                from_amount=from_amount,
                to_amount=to_amount,
                exchange_rate=round_to_two_dp(exchange_rate),
            )

            return (fx_transfer, None)

    except Wallet.DoesNotExist:
        return (None, "WALLET_DOES_NOT_EXIST")
    except Exception as e:
        return (None, f"UNEXPECTED_ERROR: {str(e)}")