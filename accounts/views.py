from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import SignUpForm, LoginForm


def register_view(request):
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

def login_view(request):
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
                form.add_error(None, "Invalid email or password")
    else:
        form = LoginForm()
    
    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    # User should be logged in to access logout
    if not request.user.is_authenticated:
        return redirect("/accounts/login/")
    
    logout(request)
    return redirect("/accounts/login/")