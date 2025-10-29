from django.http import HttpRequest, HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.accounts.models import Profile
from apps.wallets.models import Wallet

@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    profile = Profile.objects.get(user=request.user)
    wallets = Wallet.objects.filter(user=request.user).order_by('-updated_at')
    return render(request, "dashboard/dashboard.html", {"profile": profile, "wallets": wallets})
