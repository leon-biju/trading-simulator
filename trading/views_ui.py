from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET

from trading.models import Order, OrderStatus, Trade
from trading.forms import PlaceOrderForm

from trading.services.orders import  place_order, cancel_order
from trading.services.queries import get_user_positions

from market.models import Asset
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
@require_POST
def place_order_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    """Handle order placement for an asset."""

    if request.user.id is None:
        return redirect('login')  # Redundant but mypy is being pedantic

    asset = get_object_or_404(
        Asset.objects.select_related('exchange', 'currency'),
        exchange__code=exchange_code,
        ticker=asset_symbol,
    )
    
    form = PlaceOrderForm(request.POST)
    
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
        return redirect('asset_detail', exchange_code=exchange_code, asset_symbol=asset_symbol)
    
    side = form.cleaned_data['side']
    order_type = form.cleaned_data['order_type']
    quantity = form.cleaned_data['quantity']
    limit_price = form.cleaned_data.get('limit_price')
    
    try:
        order = place_order(
            user_id=request.user.id,
            asset=asset,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
        )
        
        if order.status == OrderStatus.FILLED:
            messages.success(
                request, 
                f"Order filled: {order.get_side_display()} {order.quantity} {asset.ticker}"
            )
        else:
            messages.info(
                request,
                f"Order placed: {order.get_side_display()} {order.quantity} {asset.ticker} (Pending)"
            )
            
    except ValueError as e:
        messages.error(request, str(e))
    except LookupError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
    
    return redirect('asset_detail', exchange_code=exchange_code, asset_symbol=asset_symbol)


@login_required
@require_POST
def cancel_order_view(request: HttpRequest, order_id: int) -> HttpResponse:
    if request.user.id is None:
        return redirect('login')  # Redundant but mypy is being pedantic
    try:
        order = cancel_order(order_id=order_id, user_id=request.user.id)
        messages.success(request, f"Order cancelled: {order.quantity} {order.asset.ticker}")
    except ValueError as e:
        messages.error(request, str(e))
    except LookupError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
    
    # Redirect back to the referring page or dashboard
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard')


@login_required
@require_GET
def order_history_view(request: HttpRequest) -> HttpResponse:
    """Display user's order history."""
    orders = Order.objects.filter(
        user_id=request.user.id
    ).select_related('asset').order_by('-created_at')[:100]
    
    return render(request, 'trading/order_history.html', {
        'orders': orders,
    })


@login_required
@require_GET
def trade_history_view(request: HttpRequest) -> HttpResponse:
    """Display user's trade history."""
    trades = Trade.objects.filter(
        user_id=request.user.id
    ).select_related('asset', 'order', 'fee_currency', 'asset__currency').order_by('-executed_at')[:100]
    
    from accounts.models import Profile
    profile = Profile.objects.get(user_id=request.user.id)
    home_currency = profile.home_currency
    home_code = home_currency.code

    enriched_trades = []
    for trade in trades:
        asset_currency_code = trade.asset.currency.code
        price_home = _convert_to_home(asset_currency_code, home_code, trade.price)
        total_value_home = _convert_to_home(asset_currency_code, home_code, trade.total_value)
        fee_home = _convert_to_home(trade.fee_currency.code, home_code, trade.fee)
        net_amount_home = _convert_to_home(asset_currency_code, home_code, trade.net_amount)
        enriched_trades.append({
            'trade': trade,
            'price': price_home,
            'total_value': total_value_home,
            'fee': fee_home,
            'net_amount': net_amount_home,
        })

    return render(request, 'trading/trade_history.html', {
        'trades': enriched_trades,
        'home_currency': home_currency,
    })


@login_required
@require_GET
def portfolio_view(request: HttpRequest) -> HttpResponse:
    """Display user's portfolio (positions)."""
    if request.user.id is None:
        return redirect('login')  # Redundant but mypy is being pedantic
    positions = get_user_positions(request.user.id)
    
    home_currency = request.user.home_currency
    home_code = home_currency.code

    # Enrich positions with current price and P&L data, converted to home currency
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

    return render(request, 'trading/portfolio.html', {
        'positions': enriched_positions,
        'total_value': total_value,
        'total_cost': total_cost,
        'total_pnl': total_pnl,
        'home_currency': home_currency,
    })