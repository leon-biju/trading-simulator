from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Stock, Exchange, CurrencyAsset

# Create your views here.

@login_required
def stock_performance_view(request, exchange_code, asset_symbol):
    exchange = get_object_or_404(Exchange, code=exchange_code)
    stock = get_object_or_404(Stock, exchange=exchange, symbol=asset_symbol)
    context = {
        'stock': stock,
    }
    return render(request, 'market/asset_performance.html', context)

@login_required
def currency_asset_performance_view(request, asset_symbol):
    currency_asset = get_object_or_404(CurrencyAsset, symbol=asset_symbol)
    context = {
        'currency_asset': currency_asset,
    }
    return render(request, 'market/asset_performance.html', context)


@login_required
def stock_performance_chart_data_view(request, exchange_code, asset_symbol):
    exchange = get_object_or_404(Exchange, code=exchange_code)
    stock = get_object_or_404(Stock, exchange=exchange, symbol=asset_symbol)
    price_history = stock.price_history.order_by('timestamp')

    timestamps = [p.timestamp.strftime('%Y-%m-%d %H:%M:%S') for p in price_history]
    prices = [float(p.price) for p in price_history]

    return JsonResponse({
        'timestamps': timestamps,
        'prices': prices,
        'currency_code': stock.currency.code,
    })

@login_required
def currency_asset_performance_chart_data_view(request, asset_symbol):
    currency_asset = get_object_or_404(CurrencyAsset, symbol=asset_symbol)
    price_history = currency_asset.price_history.order_by('timestamp')

    timestamps = [p.timestamp.strftime('%Y-%m-%d %H:%M:%S') for p in price_history]
    prices = [float(p.price) for p in price_history]

    return JsonResponse({
        'timestamps': timestamps,
        'prices': prices,
        'currency_code': currency_asset.currency.code,
    })