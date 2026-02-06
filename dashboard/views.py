from decimal import Decimal

from django.http import HttpRequest, HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from accounts.models import Profile
from wallets.models import Wallet
from trading.models import Order, OrderStatus, Trade
from trading.services import get_user_positions
from market.models import Currency, FXRate

@login_required
@require_GET
def dashboard_view(request: HttpRequest) -> HttpResponse:
    if request.user.id is None:
        return redirect('login') # Redundant but mypy is bieng pedantic

    profile = Profile.objects.get(user_id=request.user.id)
    wallets = Wallet.objects.filter(user_id=request.user.id).select_related('currency').order_by('-updated_at')
    base_currency = Currency.objects.filter(is_base=True).first()

    total_cash = request.user.total_cash
    
    # Get pending orders
    pending_orders = Order.objects.filter(
        user_id=request.user.id,
        status=OrderStatus.PENDING
    ).select_related('asset').order_by('-created_at')[:5]
    
    # Get recent executed trades
    recent_trades = Trade.objects.filter(
        user_id=request.user.id
    ).select_related('asset', 'fee_currency').order_by('-executed_at')[:5]
    
    # Get positions summary and enrich with current price and P&L data
    positions = get_user_positions(request.user.id)
    enriched_positions = []
    total_value = Decimal('0')
    total_cost = Decimal('0')
    
    for position in positions:
        current_price = position.asset.get_latest_price()
        unrealized_pnl = position.calculate_unrealized_pnl()
        current_value = (position.quantity * current_price) if current_price else None
        
        enriched_positions.append({
            'position': position,
            'current_price': current_price,
            'current_value': current_value,
            'unrealized_pnl': unrealized_pnl,
            'pnl_percent': (
                (unrealized_pnl / position.total_cost_basis * 100)
                if unrealized_pnl and position.total_cost_basis > 0 
                else None
            ),
        })
        
        if current_value:
            total_value += current_value
        total_cost += position.total_cost_basis
    
    total_pnl = total_value - total_cost if total_value else None
    pnl_percent = (total_pnl / total_cost * 100) if total_pnl and total_cost > 0 else None
    
    return render(request, "dashboard/dashboard.html", {
        "profile": profile, 
        "wallets": wallets,
        "pending_orders": pending_orders,
        "recent_trades": recent_trades,
        "positions": enriched_positions,
        "total_value": total_value,
        "total_cost": total_cost,
        "total_pnl": total_pnl,
        "pnl_percent": pnl_percent,
        "total_cash": total_cash,
        "base_currency": base_currency,
    })
