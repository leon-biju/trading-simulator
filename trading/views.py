from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_GET

from trading.models import Order, OrderStatus, Trade, Position
from trading.forms import PlaceOrderForm
from trading.services import (
    place_order,
    cancel_order,
    get_user_positions,
)
from market.models import Asset
from wallets.models import Wallet


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
    ).select_related('asset', 'order', 'fee_currency').order_by('-executed_at')[:100]
    
    return render(request, 'trading/trade_history.html', {
        'trades': trades,
    })


@login_required
@require_GET
def portfolio_view(request: HttpRequest) -> HttpResponse:
    """Display user's portfolio (positions)."""
    if request.user.id is None:
        return redirect('login')  # Redundant but mypy is being pedantic
    positions = get_user_positions(request.user.id)
    
    # Enrich positions with current price and P&L data
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
    
    return render(request, 'trading/portfolio.html', {
        'positions': enriched_positions,
        'total_value': total_value,
        'total_cost': total_cost,
        'total_pnl': total_value - total_cost if total_value else None,
    })


@login_required
@require_GET
def get_position_for_stock(request: HttpRequest, exchange_code: str, asset_symbol: str) -> JsonResponse:
    """API endpoint to get user's position for a specific asset."""
    asset = get_object_or_404(
        Asset.objects.select_related('exchange'),
        exchange__code=exchange_code,
        ticker=asset_symbol,
    )
    
    try:
        position = Position.objects.get(user_id=request.user.id, asset=asset)
        return JsonResponse({
            'has_position': True,
            'quantity': str(position.quantity),
            'available_quantity': str(position.available_quantity),
            'average_cost': str(position.average_cost),
        })
    except Position.DoesNotExist:
        return JsonResponse({
            'has_position': False,
            'quantity': '0',
            'available_quantity': '0',
            'average_cost': '0',
        })


@login_required
@require_GET
def get_wallet_balance(request: HttpRequest, currency_code: str) -> JsonResponse:
    """API endpoint to get user's wallet balance for a specific currency."""
    try:
        wallet = Wallet.objects.get(user_id=request.user.id, currency__code=currency_code)
        return JsonResponse({
            'has_wallet': True,
            'balance': str(wallet.balance),
            'available_balance': str(wallet.available_balance),
            'pending_balance': str(wallet.pending_balance),
            'symbol': wallet.symbol,
        })
    except Wallet.DoesNotExist:
        return JsonResponse({
            'has_wallet': False,
            'balance': '0',
            'available_balance': '0',
            'pending_balance': '0',
            'symbol': currency_code,
        })
