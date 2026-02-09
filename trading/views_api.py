from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from market.models import Asset
from wallets.models import Wallet
from trading.models import Position

from trading.services.portfolio import get_portfolio_history

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
            'symbol': wallet.currency.code,
        })
    except Wallet.DoesNotExist:
        return JsonResponse({
            'has_wallet': False,
            'balance': '0',
            'available_balance': '0',
            'pending_balance': '0',
            'symbol': currency_code,
        })


@login_required
@require_GET
def portfolio_history_api(request: HttpRequest) -> JsonResponse:
    """API endpoint to get user's portfolio history for charting."""
    assert request.user.id is not None, "Huh, shouldn't get here"  # For mypy
    
    history = get_portfolio_history(request.user.id)
    
    data = [
        {
            'date': snapshot.date.isoformat(),
            'total_value': str(snapshot.total_value),
            'total_cost': str(snapshot.total_cost),
            'cash_balance': str(snapshot.cash_balance),
        }
        for snapshot in history
    ]
    
    return JsonResponse({'history': data})