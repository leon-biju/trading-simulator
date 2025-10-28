from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Wallet
from .forms import AddFundsForm
from .services import perform_fx_transfer, DUMMY_FX_RATES
import json

ERROR_MESSAGES = {
    'ZERO_AMOUNT_TRANSACTION': 'Transaction amount cannot be zero.',
    'INSUFFICIENT_FUNDS': 'Insufficient funds in your wallet.',
    'INSUFFICIENT_FUNDS_IN_FROM_WALLET': 'Insufficient funds in the source wallet for this transfer.',
    'WALLET_DOES_NOT_EXIST': 'The specified wallet does not exist.',
    'SAME_WALLET_TRANSFER': 'Cannot transfer funds to the same wallet.',
    'UNSUPPORTED_CURRENCY': 'One or more currencies are not supported.',
    'UNSUPPORTED_CURRENCY_FOR_FX': 'Exchange rate not available for the selected currencies.',
    'SPECIFY_EITHER_FROM_OR_TO_AMOUNT': 'Invalid transfer parameters. Please try again.',
    'INVALID_FROM_AMOUNT': 'The transfer amount must be greater than zero.',
    'INVALID_TO_AMOUNT': 'The transfer amount must be greater than zero.',
}


@login_required
def wallet_detail(request, currency):
    wallet = get_object_or_404(Wallet, currency=currency, user=request.user)
    transactions = wallet.transactions.all()
    user_other_wallets = Wallet.objects.filter(user=request.user).exclude(id=wallet.id)

    if request.method == 'POST':
        form = AddFundsForm(request.POST)
        if form.is_valid():
            from_wallet_currency = form.cleaned_data['from_wallet_currency']
            to_amount = form.cleaned_data['to_amount']
            
            _, error = perform_fx_transfer(
                user_id=request.user.id,
                from_wallet_currency=from_wallet_currency,
                to_wallet_currency=wallet.currency,
                to_amount=to_amount
            )

            if error:
                error_message = ERROR_MESSAGES.get(error, 'An unknown error occurred.')
                messages.error(request, error_message)
            else:
                messages.success(request, f'Successfully added {wallet.symbol}{to_amount} to your {wallet.currency} wallet.')

            return redirect('wallets:wallet_detail', currency=wallet.currency)
        else:
            messages.error(request, 'There was an error with your submission. Please check the form and try again.')
    else: # GET requests
        form = AddFundsForm()

    base_rate = DUMMY_FX_RATES.get(wallet.currency, 1)
    exchange_rates = {curr: (rate / base_rate) for curr, rate in DUMMY_FX_RATES.items()}

    serializable_fx_rates = {k: str(v) for k, v in exchange_rates.items()}

    context = {
        'wallet': wallet,
        'transactions': transactions,
        'user_other_wallets': user_other_wallets,
        'form': form,
        'fx_rates': json.dumps(serializable_fx_rates),
    }
    return render(request, 'wallets/wallet_detail.html', context)