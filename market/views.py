from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Stock, Exchange, CurrencyAsset
from trading.models import Order, OrderStatus, Position
from trading.forms import PlaceOrderForm
from wallets.models import Wallet


@login_required
def market_overview_view(request: HttpRequest) -> HttpResponse:
    """Market overview showing all exchanges and their stocks."""
    exchanges = Exchange.objects.prefetch_related('stocks').all()
    
    # Build exchange data with market status
    exchange_data = []
    for exchange in exchanges:
        stocks = exchange.stocks.filter(is_active=True).select_related('currency')
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
    """View stocks for a specific exchange."""
    exchange = get_object_or_404(Exchange, code=exchange_code)
    stocks = Stock.objects.filter(
        exchange=exchange, 
        is_active=True
    ).select_related('currency').order_by('symbol')
    
    # Enrich stocks with current price
    stocks_with_prices = []
    for stock in stocks:
        stocks_with_prices.append({
            'stock': stock,
            'current_price': stock.get_latest_price(),
        })
    
    return render(request, 'market/exchange_detail.html', {
        'exchange': exchange,
        'is_open': exchange.is_currently_open(),
        'stocks': stocks_with_prices,
    })


@login_required
def stock_detail_view(request: HttpRequest, exchange_code: str, stock_symbol: str) -> HttpResponse:
    """Stock detail page with trading form, price chart, and market status."""
    stock = get_object_or_404(
        Stock.objects.select_related('exchange', 'currency'),
        exchange__code=exchange_code,
        symbol=stock_symbol
    )
    
    # Get current price
    current_price = stock.get_latest_price()
    
    # Get user's wallet for this currency
    wallet = None
    try:
        wallet = Wallet.objects.get(user_id=request.user.id, currency=stock.currency)
    except Wallet.DoesNotExist:
        pass
    
    # Get user's position for this stock
    position = None
    try:
        position = Position.objects.get(user_id=request.user.id, asset=stock)
    except Position.DoesNotExist:
        pass
    
    # Get user's pending orders for this stock
    pending_orders = Order.objects.filter(
        user_id=request.user.id,
        asset=stock,
        status=OrderStatus.PENDING
    ).order_by('-created_at')[:5]
    
    # Market status
    is_exchange_open = stock.exchange.is_currently_open()
    
    # Trading form
    form = PlaceOrderForm()
    
    context = {
        'stock': stock,
        'current_price': current_price,
        'wallet': wallet,
        'position': position,
        'pending_orders': pending_orders,
        'is_exchange_open': is_exchange_open,
        'form': form,
    }
    return render(request, 'market/stock_detail.html', context)


# Keep old view for backwards compatibility (redirect or keep as alias)
@login_required
def stock_performance_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    """Deprecated: Use stock_detail_view instead."""
    return stock_detail_view(request, exchange_code, asset_symbol)

@login_required
def currency_asset_performance_view(request: HttpRequest, asset_symbol: str) -> HttpResponse:
    currency_asset = get_object_or_404(CurrencyAsset, symbol=asset_symbol)
    context = {
        'currency_asset': currency_asset,
    }
    return render(request, 'market/asset_performance.html', context)


@login_required
def stock_performance_chart_data_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    stock = get_object_or_404(Stock, exchange__code=exchange_code, symbol=asset_symbol)
    daily_price_history = stock.daily_price_history.order_by('date')

    dates = [p.date.strftime('%Y-%m-%d') for p in daily_price_history]
    candlestick_data = [
        {
            'x': p.date.strftime('%Y-%m-%d'),
            'o': float(p.open_price),
            'h': float(p.high_price),
            'l': float(p.low_price),
            'c': float(p.close_price),
        }
        for p in daily_price_history
    ]

    return JsonResponse({
        'dates': dates,
        'candlestick_data': candlestick_data,
        'currency_code': stock.currency.code,
    })

@login_required
def currency_asset_performance_chart_data_view(request: HttpRequest, asset_symbol: str) -> HttpResponse:
    currency_asset = get_object_or_404(CurrencyAsset, symbol=asset_symbol)
    daily_price_history = currency_asset.daily_price_history.order_by('date')

    dates = [p.date.strftime('%Y-%m-%d') for p in daily_price_history]
    candlestick_data = [
        {
            'x': p.date.strftime('%Y-%m-%d'),
            'o': float(p.open_price),
            'h': float(p.high_price),
            'l': float(p.low_price),
            'c': float(p.close_price),
        }
        for p in daily_price_history
    ]

    return JsonResponse({
        'dates': dates,
        'candlestick_data': candlestick_data,
        'currency_code': currency_asset.currency.code,
    })