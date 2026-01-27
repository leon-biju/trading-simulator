from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator

from trading.models import OrderType, OrderSide


class PlaceOrderForm(forms.Form):
    """Form for placing buy/sell orders on stocks."""
    
    side = forms.ChoiceField(
        choices=OrderSide.choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-check'}),
        initial=OrderSide.BUY,
    )
    
    order_type = forms.ChoiceField(
        choices=OrderType.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=OrderType.MARKET,
    )
    
    quantity = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity',
            'step': '0.00000001',
            'min': '0.00000001',
        }),
    )
    
    limit_price = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        required=False,
        validators=[MinValueValidator(Decimal('0.00000001'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Limit Price',
            'step': '0.01',
            'min': '0.01',
        }),
    )
    
    def clean(self) -> dict[str, Decimal | str | None]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            raise forms.ValidationError("Invalid form data.")
        order_type = cleaned_data.get('order_type')
        limit_price = cleaned_data.get('limit_price')
        
        if order_type == OrderType.LIMIT and not limit_price:
            self.add_error('limit_price', 'Limit price is required for limit orders.')
        
        if order_type == OrderType.MARKET and limit_price:
            # Clear limit price for market orders
            cleaned_data['limit_price'] = None
        
        return cleaned_data
