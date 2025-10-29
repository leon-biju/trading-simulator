from django import forms
from .models import Currency

class AddFundsForm(forms.Form):
    from_wallet_currency = forms.ChoiceField(choices=Currency.choices)
    to_amount = forms.DecimalField(max_digits=20, decimal_places=2)