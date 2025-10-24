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
    

def perform_fx_transfer(
        user_id: int,
        from_wallet_currency: str,
        to_wallet_currency: str,
        from_amount: Decimal,
    ) -> Tuple[Optional[Fx_Transfer], Optional[str]]:
    # Transfer funds between two wallets of the same user but different currencies

    if from_wallet_currency == to_wallet_currency:
        return (None, "SAME_WALLET_TRANSFER")

    if from_wallet_currency not in Currency.values or to_wallet_currency not in Currency.values:
        return (None, "UNSUPPORTED_CURRENCY")

    try:
        with transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency=from_wallet_currency)
            to_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency=to_wallet_currency)

            if from_amount <= 0:
                return (None, "INVALID_FROM_AMOUNT")

            if from_wallet.balance < from_amount:
                return (None, "INSUFFICIENT_FUNDS_IN_FROM_WALLET")

            # Get dummy FX rates
            # USE REAL FX RATES IN PROD
            from_rate = DUMMY_FX_RATES.get(from_wallet.currency)
            to_rate = DUMMY_FX_RATES.get(to_wallet.currency)

            if not from_rate or not to_rate:
                return (None, "UNSUPPORTED_CURRENCY_FOR_FX")

            exchange_rate = to_rate / from_rate
            to_amount = round_to_two_dp(from_amount * exchange_rate)

            _, from_error = create_transaction(
                wallet_id=from_wallet.id,
                amount=-from_amount,
                source=Transaction.Source.SELL,
                description=f"FX Transfer to {to_wallet.currency} wallet"
            )
            if from_error:
                return (None, from_error)

            _, to_error = create_transaction(
                wallet_id=to_wallet.id,
                amount=to_amount,
                source=Transaction.Source.BUY,
                description=f"FX Transfer from {from_wallet.currency} wallet"
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