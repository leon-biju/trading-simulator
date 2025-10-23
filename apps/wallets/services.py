from typing import Optional, Tuple
from .models import Transaction, Wallet
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