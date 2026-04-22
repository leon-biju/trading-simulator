from decimal import Decimal

from django.db.models import Count
from django.db.models.functions import TruncWeek
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from config.pagination import StandardPagination
from config.utils import convert_to_home
from trading.serializers import (
    OrderSerializer,
    PlaceOrderSerializer,
    PortfolioSerializer,
    PositionSerializer,
    TradeSerializer,
)
from market.models import Asset, Currency
from market.services.fx import get_fx_rate
from trading.models import Order, OrderStatus, Position, PortfolioSnapshot, Trade
from trading.services.orders import cancel_order, place_order
from trading.services.portfolio import get_portfolio_history
from trading.services.queries import get_user_positions
from wallets.models import Wallet


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = cancel_order(order_id=order_id, user_id=request.user.id)
        return Response(OrderSerializer(order).data)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class TradeListView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
            labels.append(snapshot.date.isoformat())
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
    permission_classes = [IsAuthenticated]

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


@method_decorator(ratelimit(key='user', rate='20/m', block=True), name='get')
class AnalyticsStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        home_code = user.home_currency.code

        total_trades = Trade.objects.filter(user=user).count()

        traded_positions = Position.objects.filter(user=user).exclude(realized_pnl=Decimal('0'))
        total_traded = traded_positions.count()
        winning = traded_positions.filter(realized_pnl__gt=0).count()
        win_rate = float(winning / total_traded * 100) if total_traded > 0 else None

        trades_qs = Trade.objects.filter(user=user).select_related('fee_currency')
        total_fees_home = sum(
            (convert_to_home(t.fee_currency.code, home_code, t.fee) or Decimal('0'))
            for t in trades_qs
        )

        values = list(
            PortfolioSnapshot.objects
            .filter(user=user)
            .order_by('date')
            .values_list('total_portfolio_value', flat=True)
        )
        max_drawdown = None
        if values:
            peak = values[0]
            max_dd = Decimal('0')
            for v in values:
                if v > peak:
                    peak = v
                elif peak > 0:
                    dd = (peak - v) / peak * 100
                    if dd > max_dd:
                        max_dd = dd
            max_drawdown = float(max_dd)

        return Response({
            'total_trades': total_trades,
            'win_rate': win_rate,
            'winning_positions': winning,
            'total_traded_positions': total_traded,
            'total_fees_home': float(total_fees_home),
            'max_drawdown_pct': max_drawdown,
            'home_currency': home_code,
        })


@method_decorator(ratelimit(key='user', rate='20/m', block=True), name='get')
class AnalyticsAllocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        home_code = user.home_currency.code

        by_currency: dict[str, dict] = {}

        positions = (
            Position.objects
            .filter(user=user, quantity__gt=0)
            .select_related('asset', 'asset__currency')
        )
        for pos in positions:
            code = pos.asset.currency.code
            price = pos.asset.get_latest_price()
            if price is None:
                continue
            value_home = convert_to_home(code, home_code, pos.quantity * price) or Decimal('0')
            entry = by_currency.setdefault(code, {'invested': Decimal('0'), 'cash': Decimal('0')})
            entry['invested'] += value_home

        wallets = Wallet.objects.filter(user=user).select_related('currency')
        for wallet in wallets:
            code = wallet.currency.code
            cash_home = convert_to_home(code, home_code, wallet.balance) or Decimal('0')
            entry = by_currency.setdefault(code, {'invested': Decimal('0'), 'cash': Decimal('0')})
            entry['cash'] += cash_home

        total = sum(v['invested'] + v['cash'] for v in by_currency.values())
        allocations = [
            {
                'currency': code,
                'invested_home': float(v['invested']),
                'cash_home': float(v['cash']),
                'total_home': float(v['invested'] + v['cash']),
                'percent': float((v['invested'] + v['cash']) / total * 100) if total > 0 else 0,
            }
            for code, v in by_currency.items()
            if v['invested'] + v['cash'] > 0
        ]
        allocations.sort(key=lambda x: -x['total_home'])

        return Response({
            'allocations': allocations,
            'total_home': float(total),
            'home_currency': home_code,
        })


@method_decorator(ratelimit(key='user', rate='20/m', block=True), name='get')
class AnalyticsActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        activity = (
            Trade.objects
            .filter(user=request.user)
            .annotate(week=TruncWeek('executed_at'))
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
        )
        return Response([
            {'week': entry['week'].date().isoformat(), 'count': entry['count']}
            for entry in activity
        ])
