from django.http import HttpRequest, HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import Profile
from wallets.models import Wallet
from trading.models import Order, OrderStatus, Trade
from trading.services import get_user_positions

@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    if request.user.id is None:
        return redirect('login') # Redundant but mypy is bieng pedantic

    profile = Profile.objects.get(user_id=request.user.id)
    wallets = Wallet.objects.filter(user_id=request.user.id).order_by('-updated_at')
    
    # Get pending orders
    pending_orders = Order.objects.filter(
        user_id=request.user.id,
        status=OrderStatus.PENDING
    ).select_related('asset').order_by('-created_at')[:5]
    
    # Get recent executed trades
    recent_trades = Trade.objects.filter(
        user_id=request.user.id
    ).select_related('asset', 'fee_currency').order_by('-executed_at')[:5]
    
    # Get positions summary
    positions = get_user_positions(request.user.id)
    
    return render(request, "dashboard/dashboard.html", {
        "profile": profile, 
        "wallets": wallets,
        "pending_orders": pending_orders,
        "recent_trades": recent_trades,
        "positions": positions,
    })
