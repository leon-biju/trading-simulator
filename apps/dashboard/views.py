from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from apps.accounts.models import Profile
from apps.wallets.models import Wallet

@login_required
def dashboard_view(request):
    profile = Profile.objects.get(user=request.user)
    wallet = Wallet.objects.get(user=request.user)
    print(f"User: {profile.user.username}, Cash Balance: {wallet.balance}")
    return render(request, "dashboard/dashboard.html", {"profile": profile, "wallet": wallet})
