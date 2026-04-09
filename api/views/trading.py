from decimal import Decimal

from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from api.pagination import StandardPagination
from api.serializers.trading import (
    OrderSerializer,
    PlaceOrderSerializer,
    PortfolioSerializer,
    PositionSerializer,
    TradeSerializer,
)
from market.models import Asset, Currency
from market.services.fx import get_fx_rate
from trading.models import Order, OrderStatus, Position, Trade
from trading.services.orders import cancel_order, place_order
from trading.services.portfolio import get_portfolio_history
from trading.services.queries import get_user_positions


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class OrderListCreateView(APIView):
    def get(self, request):
        """Paginated order history."""
        orders = (
            Order.objects.filter(user_id=request.user.id)
            .select_related('asset', 'asset__exchange')
            .order_by('-created_at')
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(orders, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @method_decorator(ratelimit(key='user', rate='30/m', block=True))
    def post(self, request):
        """Place a new order."""
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            asset = Asset.objects.select_related('exchange', 'currency').get(
                exchange__code=data['exchange_code'],
                ticker=data['asset_symbol'],
            )
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        order = place_order(
            user_id=request.user.id,
            asset=asset,
            side=data['side'],
            quantity=data['quantity'],
            order_type=data['order_type'],
            limit_price=data.get('limit_price'),
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@method_decorator(ratelimit(key='user', rate='30/m', block=True), name='post')
class CancelOrderView(APIView):
    def post(self, request, order_id):
        order = cancel_order(order_id=order_id, user_id=request.user.id)
        return Response(OrderSerializer(order).data)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class TradeListView(APIView):
    def get(self, request):
        profile = Profile.objects.get(user_id=request.user.id)
        home_code = profile.home_currency.code

        trades = (
            Trade.objects.filter(user_id=request.user.id)
            .select_related('asset', 'asset__exchange', 'asset__currency', 'fee_currency')
            .order_by('-executed_at')
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(trades, request)
        serializer = TradeSerializer(page, many=True, context={'home_currency_code': home_code})
        return paginator.get_paginated_response(serializer.data)


@method_decorator(ratelimit(key='user', rate='30/m', block=True), name='get')
class PortfolioView(APIView):
    def get(self, request):
        home_currency = request.user.home_currency
        home_code = home_currency.code

        positions = list(
            Position.objects.filter(user_id=request.user.id, quantity__gt=0)
            .select_related('asset', 'asset__currency', 'asset__exchange')
        )

        context = {'home_currency_code': home_code}
        position_data = PositionSerializer(positions, many=True, context=context).data

        total_value = Decimal('0')
        total_cost = Decimal('0')
        for pos_serialized, pos_obj in zip(position_data, positions):
            cv = pos_serialized.get('current_value_home')
            cb = pos_serialized.get('cost_basis_home')
            if cv:
                total_value += Decimal(cv)
            if cb:
                total_cost += Decimal(cb)

        total_pnl = total_value - total_cost if total_value else None
        pnl_percent = float(total_pnl / total_cost * 100) if total_pnl and total_cost > 0 else None

        return Response({
            'home_currency': home_code,
            'total_value': str(total_value),
            'total_cost': str(total_cost),
            'total_pnl': str(total_pnl) if total_pnl is not None else None,
            'pnl_percent': pnl_percent,
            'positions': position_data,
        })


@method_decorator(ratelimit(key='user', rate='20/m', block=True), name='get')
class PortfolioHistoryView(APIView):
    """Mirrors the existing portfolio_history_api, now under /api/."""

    def get(self, request):
        range_param = request.GET.get('range', '1M')
        days_map = {'1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 365, 'ALL': None}
        days = days_map.get(range_param, 30)

        history = get_portfolio_history(request.user.id, days=days)

        profile = Profile.objects.get(user_id=request.user.id)
        home_code = profile.home_currency.code
        base_currency = Currency.objects.filter(is_base=True).first()

        fx_multiplier = 1.0
        if base_currency and base_currency.code != home_code:
            rate = get_fx_rate(base_currency.code, home_code)
            if rate is not None:
                fx_multiplier = float(rate)

        labels, total_assets, portfolio_value, cash_balance = [], [], [], []
        for snapshot in history:
            labels.append(snapshot.date.strftime('%d %b'))
            total_assets.append(float(snapshot.total_value + snapshot.cash_balance) * fx_multiplier)
            portfolio_value.append(float(snapshot.total_value) * fx_multiplier)
            cash_balance.append(float(snapshot.cash_balance) * fx_multiplier)

        return Response({
            'labels': labels,
            'datasets': {
                'total_assets': total_assets,
                'portfolio_value': portfolio_value,
                'cash_balance': cash_balance,
            },
            'currency': home_code,
        })


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class PositionView(APIView):
    def get(self, request, exchange_code, ticker):
        try:
            asset = Asset.objects.select_related('exchange', 'currency').get(
                exchange__code=exchange_code,
                ticker=ticker,
            )
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            position = Position.objects.select_related('asset', 'asset__currency', 'asset__exchange').get(
                user_id=request.user.id, asset=asset
            )
            home_code = request.user.home_currency.code
            data = PositionSerializer(position, context={'home_currency_code': home_code}).data
            data['has_position'] = True
            return Response(data)
        except Position.DoesNotExist:
            return Response({'has_position': False})
