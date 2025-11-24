from typing import Optional, Tuple

from .models import Fx_Transfer, Transaction, Wallet

from apps.market.models import Currency, CurrencyAsset
from apps.market.services import get_fx_rate, get_fx_conversion
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP



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
        from_wallet_currency_code: str,
        to_wallet_currency_code: str,
        from_amount: Optional[Decimal] = None,
        to_amount: Optional[Decimal] = None,
    ) -> Tuple[Optional[Fx_Transfer], Optional[str]]:
    # Transfer funds between two wallets of the same user but different currencies
    # Specify either from_amount OR to_amount, not both
    if from_wallet_currency_code == to_wallet_currency_code:
        return (None, "SAME_WALLET_TRANSFER")

    from_amount, to_amount, error = get_fx_conversion(
        from_currency_code=from_wallet_currency_code,
        to_currency_code=to_wallet_currency_code,
        from_amount=from_amount,
        to_amount=to_amount
    )

    if error:
        return (None, error)

    
    try:
        with transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency__code=from_wallet_currency_code)
            to_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency__code=to_wallet_currency_code)
            if from_wallet.balance < from_amount:
                return (None, "INSUFFICIENT_FUNDS_IN_FROM_WALLET")

            # Get FX rates for exchange rate calculation
            exchange_rate = get_fx_rate(
                from_currency_code=from_wallet_currency_code,
                to_currency_code=to_wallet_currency_code
            )

            _, from_error = create_transaction(
                wallet_id=from_wallet.id,
                amount=-from_amount,
                source=Transaction.Source.FX_TRANSFER,
                description=f"{from_wallet.currency.code} {from_amount:,.2f} → {to_wallet.currency.code} {to_amount:,.2f} @ 1 {from_wallet.currency.code} = {round_to_two_dp(exchange_rate):,.4f} {to_wallet.currency.code}"
            )
            if from_error:
                return (None, from_error)

            _, to_error = create_transaction(
                wallet_id=to_wallet.id,
                amount=to_amount,
                source=Transaction.Source.FX_TRANSFER,
                description=f"{from_wallet.currency.code} {from_amount:,.2f} → {to_wallet.currency.code} {to_amount:,.2f} @ 1 {to_wallet.currency.code} = {round_to_two_dp(1/exchange_rate):,.4f} {from_wallet.currency.code}"
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