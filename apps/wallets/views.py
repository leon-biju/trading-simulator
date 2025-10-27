from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Wallet
from .forms import AddFundsForm
from .services import perform_fx_transfer, DUMMY_FX_RATES
import json

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
                # TODO: Handle error display on frontend
                print(f"ERROR for user {request.user.id}: {error}")
                pass
            return redirect('wallets:wallet_detail', currency=wallet.currency)
    else:
        form = AddFundsForm()

    serializable_fx_rates = {k: str(v) for k, v in DUMMY_FX_RATES.items()}

    context = {
        'wallet': wallet,
        'transactions': transactions,
        'user_other_wallets': user_other_wallets,
        'form': form,
        'fx_rates': json.dumps(serializable_fx_rates),
    }
    return render(request, 'wallets/wallet_detail.html', context)