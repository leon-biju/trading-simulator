from typing import Optional, Tuple

from .models import Fx_Transfer, Transaction, Wallet

from market.models import Currency
from market.services import get_fx_rate, get_fx_conversion
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP



def round_to_two_dp(value: Decimal) -> Decimal:
    return value.quantize(Decimal('1.00'), rounding=ROUND_HALF_UP)

def create_transaction(
    wallet: Wallet,
    amount: Decimal,
    source: Transaction.Source,
    description: str,
) -> Transaction:
    if amount == 0:
        raise ValueError("Zero-amount transaction")

    with transaction.atomic():
        # Lock wallet row
        locked_wallet = (
            Wallet.objects
            .select_for_update()
            .get(pk=wallet.pk)
        )

        new_balance = locked_wallet.balance + amount
        if new_balance < 0:
            raise ValueError("Insufficient funds")

        tx = Transaction.objects.create(
            wallet=locked_wallet,
            amount=amount,
            balance_after=round_to_two_dp(new_balance),
            source=source,
            description=description,
        )

        locked_wallet.balance = new_balance
        locked_wallet.save(update_fields=["balance", "updated_at"])

        return tx

    

def perform_fx_transfer(
        user_id: int,
        from_wallet_currency_code: str,
        to_wallet_currency_code: str,
        from_amount: Optional[Decimal] = None,
        to_amount: Optional[Decimal] = None,
    ) -> Fx_Transfer:
    """
    Transfer funds between two wallets of the same user but different currencies.
    Specify either from_amount OR to_amount, not both.
    
    Raises:
        ValueError: If same currency or insufficient funds
        LookupError: If wallet or FX rate not found
        RuntimeError: For unexpected failures
    """
    if from_wallet_currency_code == to_wallet_currency_code:
        raise ValueError("Cannot perform FX transfer between same currency wallets")
    from_amount, to_amount = get_fx_conversion(
        from_currency_code=from_wallet_currency_code,
        to_currency_code=to_wallet_currency_code,
        from_amount=from_amount,
        to_amount=to_amount
    )

    try:
        with transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency__code=from_wallet_currency_code)
            to_wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency__code=to_wallet_currency_code)
            if from_wallet.available_balance < from_amount:
                raise ValueError("Insufficient funds in from_wallet")

            # Get FX rates for exchange rate calculation
            exchange_rate = get_fx_rate(
                from_currency_code=from_wallet_currency_code,
                to_currency_code=to_wallet_currency_code
            )

            if exchange_rate is None:
                raise LookupError("FX rate not available")
            
            create_transaction(
                wallet=from_wallet,
                amount=-from_amount,
                source=Transaction.Source.FX_TRANSFER,
                description=f"{from_wallet.currency.code} {from_amount:,.2f} → {to_wallet.currency.code} {to_amount:,.2f} @ 1 {from_wallet.currency.code} = {round_to_two_dp(exchange_rate):,.4f} {to_wallet.currency.code}"
            )

            create_transaction(
                wallet=to_wallet,
                amount=to_amount,
                source=Transaction.Source.FX_TRANSFER,
                description=f"{from_wallet.currency.code} {from_amount:,.2f} → {to_wallet.currency.code} {to_amount:,.2f} @ 1 {to_wallet.currency.code} = {round_to_two_dp(1/exchange_rate):,.4f} {from_wallet.currency.code}"
            )

            fx_transfer = Fx_Transfer.objects.create(
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                from_amount=from_amount,
                to_amount=to_amount,
                exchange_rate=round_to_two_dp(exchange_rate),
            )

            return fx_transfer

    except Wallet.DoesNotExist:
        raise LookupError("Wallet does not exist")
    except (ValueError, LookupError):
        # Re-raise validation and lookup errors as-is
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error during FX transfer: {str(e)}")