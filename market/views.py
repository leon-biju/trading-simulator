import datetime

from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Asset, Exchange, PriceCandle
from trading.models import Order, OrderStatus, Position
from trading.forms import PlaceOrderForm
from wallets.models import Wallet
from .services import get_asset_timezone, get_candles_for_range


RANGE_TO_DAYS = {
    "hour": 1 / 24,
    "day": 1,
    "month": 30,
    "6m": 180,
    "year": 365,
}


@login_required
def market_overview_view(request: HttpRequest) -> HttpResponse:
    """Market overview showing all exchanges and their stocks."""
    exchanges = Exchange.objects.all()
    
    # Build exchange data with market status
    exchange_data = []
    for exchange in exchanges:
        stocks = Asset.objects.filter(
            exchange=exchange,
            asset_type='STOCK',
            is_active=True,
        ).select_related('currency')
        # Enrich stocks with current price
        stocks_with_prices = []
        for stock in stocks:
            stocks_with_prices.append({
                'stock': stock,
                'current_price': stock.get_latest_price(),
            })
        
        exchange_data.append({
            'exchange': exchange,
            'is_open': exchange.is_currently_open(),
            'stocks': stocks_with_prices,
            'stock_count': len(stocks_with_prices),
        })
    
    return render(request, 'market/market_overview.html', {
        'exchanges': exchange_data,
    })


@login_required
def exchange_detail_view(request: HttpRequest, exchange_code: str) -> HttpResponse:
    """View assets for a specific exchange."""
    exchange = get_object_or_404(Exchange, code=exchange_code)
    assets = Asset.objects.filter(
        exchange=exchange,
        is_active=True,
    ).select_related('currency').order_by('ticker')
    
    # Enrich assets with current price
    assets_with_prices = []
    for asset in assets:
        assets_with_prices.append({
            'asset': asset,
            'current_price': asset.get_latest_price(),
        })
    
    return render(request, 'market/exchange_detail.html', {
        'exchange': exchange,
        'is_open': exchange.is_currently_open(),
        'assets': assets_with_prices,
    })


@login_required
def asset_detail_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    """Asset detail page with trading form, price chart, and market status."""
    asset = get_object_or_404(
        Asset.objects.select_related('exchange', 'currency'),
        exchange__code=exchange_code,
        ticker=asset_symbol,
    )
    
    # Get current price
    current_price = asset.get_latest_price()
    
    # Get user's wallet for this currency
    wallet = None
    try:
        wallet = Wallet.objects.get(user_id=request.user.id, currency=asset.currency)
    except Wallet.DoesNotExist:
        pass
    
    # Get user's position for this stock
    position = None
    try:
        position = Position.objects.get(user_id=request.user.id, asset=asset)
    except Position.DoesNotExist:
        pass
    
    # Get user's pending orders for this stock
    pending_orders = Order.objects.filter(
        user_id=request.user.id,
        asset=asset,
        status=OrderStatus.PENDING
    ).order_by('-created_at')[:5]
    
    # Market status
    is_exchange_open = asset.exchange.is_currently_open()
    
    # Trading form
    form = PlaceOrderForm()
    
    context = {
        'asset': asset,
        'current_price': current_price,
        'wallet': wallet,
        'position': position,
        'pending_orders': pending_orders,
        'is_exchange_open': is_exchange_open,
        'form': form,
    }
    return render(request, 'market/asset_detail.html', context)


# Keep old view for backwards compatibility (redirect or keep as alias)
@login_required
def asset_performance_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    """Deprecated: Use asset_detail_view instead."""
    return asset_detail_view(request, exchange_code, asset_symbol)


@login_required
def asset_performance_chart_data_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    asset = get_object_or_404(
        Asset,
        exchange__code=exchange_code,
        ticker=asset_symbol,
    )
    range_key = request.GET.get("range", "month")
    tz = get_asset_timezone(asset)
    now_local = timezone.now().astimezone(tz)

    if range_key == "hour":
        start_at = now_local - datetime.timedelta(hours=1)
        candles = get_candles_for_range(
            asset,
            start_at=start_at,
            end_at=now_local,
            interval_minutes=5,
        )
        return JsonResponse({
            "chart_type": "candlestick",
            "candlestick_data": candles,
            "currency_code": asset.currency.code,
        })

    if range_key == "day":
        start_at = now_local - datetime.timedelta(days=1)
        candles = get_candles_for_range(
            asset,
            start_at=start_at,
            end_at=now_local,
            interval_minutes=60,
        )
        return JsonResponse({
            "chart_type": "candlestick",
            "candlestick_data": candles,
            "currency_code": asset.currency.code,
        })

    if range_key == "month":
        start_at = now_local - datetime.timedelta(days=RANGE_TO_DAYS["month"] - 1)
        candlestick_data = get_candles_for_range(
            asset,
            start_at=start_at,
            end_at=now_local,
            interval_minutes=1440,
        )
        return JsonResponse({
            "chart_type": "candlestick",
            "candlestick_data": candlestick_data,
            "currency_code": asset.currency.code,
        })

    start_days = RANGE_TO_DAYS.get(range_key, RANGE_TO_DAYS["month"])
    start_at = now_local - datetime.timedelta(days=start_days - 1)
    daily_candles = PriceCandle.objects.filter(
        asset=asset,
        interval_minutes=1440,
        start_at__gte=start_at,
        start_at__lte=now_local,
    ).order_by("start_at")

    line_series = [
        {
            "x": candle.start_at.date().isoformat(),
            "y": float(candle.close_price),
        }
        for candle in daily_candles
    ]

    return JsonResponse({
        "chart_type": "line",
        "line_series": line_series,
        "currency_code": asset.currency.code,
    })
