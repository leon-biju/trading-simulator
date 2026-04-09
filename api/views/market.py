import datetime

from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from market.models import Asset, Exchange, FXRate, PriceCandle
from trading.models import Order, OrderStatus, Position
from wallets.models import Wallet
from market.services.candles import get_asset_timezone, get_candles_for_range

from api.serializers.market import (
    AssetDetailSerializer,
    AssetListSerializer,
    ExchangeSerializer,
    FxRateSerializer,
)


RANGE_TO_DAYS = {
    "hour": 1 / 24,
    "day": 1,
    "month": 30,
    "6m": 180,
    "year": 365,
}


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class ExchangeListView(APIView):
    def get(self, request):
        exchanges = Exchange.objects.prefetch_related('asset_set__currency').all()
        data = []
        for exchange in exchanges:
            assets = [
                a for a in exchange.asset_set.all() if a.is_active
            ]
            serializer = ExchangeSerializer(exchange)
            exchange_data = serializer.data
            exchange_data['assets'] = AssetListSerializer(assets, many=True).data
            exchange_data['asset_count'] = len(assets)
            data.append(exchange_data)

        # Sort: open exchanges first, then by hours until open, then name
        data.sort(key=lambda e: (
            not e['is_open'],
            e['hours_until_open'] if e['hours_until_open'] is not None else 999999,
            e['name'].lower(),
        ))
        return Response(data)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class ExchangeDetailView(APIView):
    def get(self, request, exchange_code):
        try:
            exchange = Exchange.objects.prefetch_related('asset_set__currency').get(code=exchange_code)
        except Exchange.DoesNotExist:
            return Response({'error': 'Exchange not found'}, status=status.HTTP_404_NOT_FOUND)

        assets = [a for a in exchange.asset_set.all() if a.is_active]
        assets.sort(key=lambda a: a.ticker)

        data = ExchangeSerializer(exchange).data
        data['assets'] = AssetListSerializer(assets, many=True).data
        return Response(data)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class AssetDetailView(APIView):
    def get(self, request, exchange_code, ticker):
        try:
            asset = Asset.objects.select_related('exchange', 'currency').get(
                exchange__code=exchange_code,
                ticker=ticker,
            )
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        # User wallet for this asset's currency
        wallet = Wallet.objects.filter(
            user_id=request.user.id,
            currency=asset.currency,
        ).first()

        # User position for this asset
        position = Position.objects.filter(
            user_id=request.user.id,
            asset=asset,
        ).first()

        # Pending orders for this asset
        pending_orders = list(
            Order.objects.filter(
                user_id=request.user.id,
                asset=asset,
                status=OrderStatus.PENDING,
            ).order_by('-created_at')[:5]
        )

        serializer = AssetDetailSerializer(asset, context={
            'wallet': wallet,
            'position': position,
            'pending_orders': pending_orders,
        })
        return Response(serializer.data)


@method_decorator(ratelimit(key='user', rate='30/m', block=True), name='get')
class ChartDataView(APIView):
    """Mirrors the existing asset_performance_chart_data_view, now under /api/."""

    def get(self, request, exchange_code, ticker):
        try:
            asset = Asset.objects.select_related('currency').get(
                exchange__code=exchange_code,
                ticker=ticker,
            )
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        range_key = request.GET.get('range', 'month')
        tz = get_asset_timezone(asset)
        now_local = timezone.now().astimezone(tz)

        if range_key == 'hour':
            start_at = now_local - datetime.timedelta(hours=1)
            candles = get_candles_for_range(asset, start_at=start_at, end_at=now_local, interval_minutes=5)
            return Response({'chart_type': 'candlestick', 'candlestick_data': candles, 'currency_code': asset.currency.code})

        if range_key == 'day':
            start_at = now_local - datetime.timedelta(days=1)
            candles = get_candles_for_range(asset, start_at=start_at, end_at=now_local, interval_minutes=60)
            return Response({'chart_type': 'candlestick', 'candlestick_data': candles, 'currency_code': asset.currency.code})

        if range_key == 'month':
            start_at = now_local - datetime.timedelta(days=29)
            candles = get_candles_for_range(asset, start_at=start_at, end_at=now_local, interval_minutes=1440)
            return Response({'chart_type': 'candlestick', 'candlestick_data': candles, 'currency_code': asset.currency.code})

        # 6m / year — line chart
        start_days = RANGE_TO_DAYS.get(range_key, RANGE_TO_DAYS['month'])
        start_at = now_local - datetime.timedelta(days=start_days - 1)
        daily_candles = PriceCandle.objects.filter(
            asset=asset,
            interval_minutes=1440,
            start_at__gte=start_at,
            start_at__lte=now_local,
        ).order_by('start_at')

        line_series = [
            {'x': c.start_at.date().isoformat(), 'y': float(c.close_price)}
            for c in daily_candles
        ]
        return Response({'chart_type': 'line', 'line_series': line_series, 'currency_code': asset.currency.code})


@method_decorator(ratelimit(key='user', rate='30/m', block=True), name='get')
class FxRatesView(APIView):
    """All FX rates, used by the wallet FX transfer preview in React."""

    def get(self, request):
        rates = FXRate.objects.select_related('base_currency', 'target_currency').all()
        serializer = FxRateSerializer(rates, many=True)
        return Response(serializer.data)
