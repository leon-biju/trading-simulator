from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
import datetime
from django.utils import timezone

from market.models import Asset, PriceCandle
from wallets.models import Wallet
from trading.models import Position

from trading.services.portfolio import get_portfolio_history

from market.services.candles import get_asset_timezone, get_candles_for_range


RANGE_TO_DAYS = {
    "hour": 1 / 24,
    "day": 1,
    "month": 30,
    "6m": 180,
    "year": 365,
}

@login_required
@require_GET
def asset_performance_chart_data_view(request: HttpRequest, exchange_code: str, asset_symbol: str) -> JsonResponse:
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
