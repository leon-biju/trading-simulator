from decimal import Decimal

from django.http import HttpRequest, HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from accounts.models import Profile
from wallets.models import Wallet
from trading.models import Order, OrderStatus, Trade
from trading.services.queries import get_user_positions
from market.models import Currency, FXRate
from market.services.fx import get_fx_conversion


def _convert_to_home(from_currency_code: str, home_currency_code: str, amount: Decimal | None) -> Decimal | None:
    """Convert an amount from an asset's native currency to the user's home currency."""
    if amount is None:
        return None
    if from_currency_code == home_currency_code:
        return amount
    _, converted = get_fx_conversion(
        from_currency_code=from_currency_code,
        to_currency_code=home_currency_code,
        from_amount=amount,
        to_amount=None,
    )
    return converted


@login_required
@require_GET
def dashboard_view(request: HttpRequest) -> HttpResponse:
    if request.user.id is None:
        return redirect('login') # Redundant but mypy is bieng pedantic

    profile = Profile.objects.get(user_id=request.user.id)
    wallets = Wallet.objects.filter(user_id=request.user.id).select_related('currency').order_by('-updated_at')
    home_currency = profile.home_currency
    home_code = home_currency.code

    total_cash = request.user.total_cash  # Already converted to home currency
    
    # Get pending orders
    pending_orders = Order.objects.filter(
        user_id=request.user.id,
        status=OrderStatus.PENDING
    ).select_related('asset').order_by('-created_at')[:5]
    
    # Get recent executed trades
    recent_trades_qs = Trade.objects.filter(
        user_id=request.user.id
    ).select_related('asset', 'asset__currency', 'fee_currency').order_by('-executed_at')[:5]
    
    recent_trades = []
    for trade in recent_trades_qs:
        price_home = _convert_to_home(trade.asset.currency.code, home_code, trade.price)
        recent_trades.append({
            'trade': trade,
            'price': price_home,
        })
    
    # Get positions summary and enrich with current price and P&L data
    # All monetary values are converted from the asset's native currency to home currency
    positions = get_user_positions(request.user.id)
    enriched_positions = []
    total_value = Decimal('0')
    total_cost = Decimal('0')
    
    for position in positions:
        asset_currency_code = position.asset.currency.code
        current_price = position.asset.get_latest_price()
        unrealized_pnl = position.calculate_unrealized_pnl()
        current_value = (position.quantity * current_price) if current_price else None

        # Convert per-position values to home currency for display
        current_value_home = _convert_to_home(asset_currency_code, home_code, current_value)
        unrealized_pnl_home = _convert_to_home(asset_currency_code, home_code, unrealized_pnl)
        cost_basis_home = _convert_to_home(asset_currency_code, home_code, position.total_cost_basis)
        avg_cost_home = _convert_to_home(asset_currency_code, home_code, position.average_cost)
        current_price_home = _convert_to_home(asset_currency_code, home_code, current_price)
        realized_pnl_home = _convert_to_home(asset_currency_code, home_code, position.realized_pnl)

        enriched_positions.append({
            'position': position,
            'current_price': current_price_home,
            'current_value': current_value_home,
            'unrealized_pnl': unrealized_pnl_home,
            'avg_cost': avg_cost_home,
            'realized_pnl': realized_pnl_home,
            'pnl_percent': (
                (unrealized_pnl / position.total_cost_basis * 100)
                if unrealized_pnl and position.total_cost_basis > 0 
                else None
            ),
        })
        
        if current_value_home:
            total_value += current_value_home
        if cost_basis_home:
            total_cost += cost_basis_home
    
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
        "home_currency": home_currency,
    })
