from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import SignUpForm, LoginForm


def register_view(request: HttpRequest) -> HttpResponse:
    # User shouldn't be logged in to access the register page
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            return redirect("/dashboard/")
        
    else:
        form = SignUpForm()
    
    return render(request, "accounts/register.html", {"form": form})


def login_view(request: HttpRequest) -> HttpResponse:
    # User shouldn't be logged in to access the login page
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            # Use username if your authentication backend does not support email
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("/dashboard/")
            else:
                form.add_error(None, "Invalid username or password")
    else:
        form = LoginForm()
    
    return render(request, "accounts/login.html", {"form": form})

@login_required
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    
    return redirect("/accounts/login/")