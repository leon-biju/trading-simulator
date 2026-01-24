from django.http import HttpRequest, HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import Profile
from wallets.models import Wallet

@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    profile = Profile.objects.get(user_id=request.user.id)
    wallets = Wallet.objects.filter(user_id=request.user.id).order_by('-updated_at')
    return render(request, "dashboard/dashboard.html", {"profile": profile, "wallets": wallets})
