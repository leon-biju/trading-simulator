from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from accounts.models import Profile
from market.models import Asset, Currency
from market.services.fx import get_fx_rate
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
    
    # Parse range parameter (default 1M = ~30 days)
    range_param = request.GET.get('range', '1M')
    days_map = {
        '1W': 7,
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
        'ALL': None,
    }
    days = days_map.get(range_param, 30)
    
    history = get_portfolio_history(request.user.id, days=days)
    
    # Determine conversion rate from base currency to user's home currency
    profile = Profile.objects.get(user_id=request.user.id)
    home_currency = profile.home_currency
    home_code = home_currency.code
    base_currency = Currency.objects.filter(is_base=True).first()
    
    fx_multiplier = 1.0
    if base_currency and base_currency.code != home_code:
        rate = get_fx_rate(base_currency.code, home_code)
        if rate is not None:
            fx_multiplier = float(rate)

    # Transform data into format expected by Chart.js
    labels = []
    total_assets = []
    portfolio_value = []
    cash_balance = []
    
    for snapshot in history:
        labels.append(snapshot.date.strftime('%d %b'))
        # Total assets = portfolio value + cash, converted to home currency
        total_assets.append(float(snapshot.total_value + snapshot.cash_balance) * fx_multiplier)
        portfolio_value.append(float(snapshot.total_value) * fx_multiplier)
        cash_balance.append(float(snapshot.cash_balance) * fx_multiplier)
    
    return JsonResponse({
        'labels': labels,
        'datasets': {
            'total_assets': total_assets,
            'portfolio_value': portfolio_value,
            'cash_balance': cash_balance,
        },
        'currency': home_code,
    })