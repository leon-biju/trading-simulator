from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.decorators import login_required
from  accounts.models import Profile

@login_required
def dashboard_view(request):
    profile = Profile.objects.get(user=request.user)
    print(f"User: {profile.user.username}, Cash Balance: {profile.cash_balance}")
    return render(request, "dashboard/dashboard.html", {"profile": profile})
