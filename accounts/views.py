from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignUpForm


def register_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            return redirect("/dashboard/")
        
    else:
        form = SignUpForm()
    
    return render(request, "accounts/register.html", {"form": form})