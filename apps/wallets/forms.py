from django import forms
from apps.market.models import Currency

class AddFundsForm(forms.Form):
    from_wallet_currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        to_field_name='code',
        empty_label=None,
        label='From Wallet'
    )
    to_amount = forms.DecimalField(
        max_digits=20, 
        decimal_places=2,
        label='Amount to Add'
    )