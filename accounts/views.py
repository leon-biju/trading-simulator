from django.shortcuts import render, redirect
from .forms import SignUpForm


def register_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/")
        
    else:
        form = SignUpForm()
    
    return render(request, "accounts/register.html", {"form": form})