# mypy: disable-error-code=type-arg

from typing import cast

from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth import get_user_model

from .models import CustomUser

from market.models import Currency


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    home_currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        required=True,
    )

    class Meta:
        model  = CustomUser
        fields = ("username", "email")

    #Reject emails that only differ in case
    def clean_email(self) -> str:
        return cast(str, self.cleaned_data["email"]).lower()

    def save(self, commit: bool = True) -> CustomUser:
        user = super().save(commit=False)
        assert isinstance(user, CustomUser)  # For mypy
        # Stash the selected currency on the instance so the
        # post_save signal can forward it to Profile.create().
        user._home_currency = self.cleaned_data["home_currency"]  # type: ignore[attr-defined]
        if commit:
            user.save()
        return user
    

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
