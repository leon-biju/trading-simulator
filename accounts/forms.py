from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model  = User
        fields = ("username", "email")

    #Reject emails that only differ in case
    def clean_email(self):
        return self.cleaned_data["email"].lower()
    

class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_username(self):
        return self.cleaned_data["username"].lower()
    
    def clean_password(self):
        return self.cleaned_data["password"]