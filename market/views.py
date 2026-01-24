from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Stock, Exchange, CurrencyAsset

# Create your views here.

@login_required
def stock_performance_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> HttpResponse:
    exchange = get_object_or_404(Exchange, code=exchange_code)
    stock = get_object_or_404(Stock, exchange=exchange, symbol=asset_symbol)
    context = {
        'stock': stock,
    }
    return render(request, 'market/asset_performance.html', context)

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