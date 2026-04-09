from decimal import Decimal
from typing import Optional
from rest_framework import serializers

from trading.models import Order, OrderSide, OrderStatus, OrderType, Position, Trade
from api.utils import convert_to_home


class OrderSerializer(serializers.ModelSerializer):
    asset_ticker = serializers.CharField(source='asset.ticker')
    exchange_code = serializers.CharField(source='asset.exchange.code')
    asset_name = serializers.CharField(source='asset.name')

    class Meta:
        model = Order
        fields = [
            'id', 'asset_ticker', 'asset_name', 'exchange_code',
            'side', 'order_type', 'quantity', 'limit_price',
            'reserved_amount', 'status',
            'created_at', 'updated_at', 'cancelled_at',
        ]


class PlaceOrderSerializer(serializers.Serializer):
    exchange_code = serializers.CharField(max_length=10)
    asset_symbol = serializers.CharField(max_length=10)
    side = serializers.ChoiceField(choices=OrderSide.choices)
    order_type = serializers.ChoiceField(choices=OrderType.choices)
    quantity = serializers.DecimalField(max_digits=20, decimal_places=8)
    limit_price = serializers.DecimalField(max_digits=20, decimal_places=8, required=False, allow_null=True)

    def validate(self, data):
        if data['order_type'] == OrderType.LIMIT and not data.get('limit_price'):
            raise serializers.ValidationError({'limit_price': 'Limit price is required for LIMIT orders.'})
        if data['order_type'] == OrderType.MARKET:
            data['limit_price'] = None
        return data


class TradeSerializer(serializers.ModelSerializer):
    asset_ticker = serializers.CharField(source='asset.ticker')
    asset_name = serializers.CharField(source='asset.name')
    exchange_code = serializers.CharField(source='asset.exchange.code')
    asset_currency_code = serializers.CharField(source='asset.currency.code')
    fee_currency_code = serializers.CharField(source='fee_currency.code')
    total_value = serializers.SerializerMethodField()
    net_amount = serializers.SerializerMethodField()
    # Home-currency equivalents — populated via serializer context
    price_home = serializers.SerializerMethodField()
    total_value_home = serializers.SerializerMethodField()
    fee_home = serializers.SerializerMethodField()
    net_amount_home = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = [
            'id', 'asset_ticker', 'asset_name', 'exchange_code',
            'asset_currency_code', 'side',
            'quantity', 'price', 'fee', 'fee_currency_code',
            'total_value', 'net_amount',
            'price_home', 'total_value_home', 'fee_home', 'net_amount_home',
            'executed_at',
        ]

    def get_total_value(self, obj):
        return str(obj.total_value)

    def get_net_amount(self, obj):
        return str(obj.net_amount)

    def _home_code(self):
        return self.context.get('home_currency_code', '')

    def get_price_home(self, obj):
        val = convert_to_home(obj.asset.currency.code, self._home_code(), obj.price)
        return str(val) if val is not None else None

    def get_total_value_home(self, obj):
        val = convert_to_home(obj.asset.currency.code, self._home_code(), obj.total_value)
        return str(val) if val is not None else None

    def get_fee_home(self, obj):
        val = convert_to_home(obj.fee_currency.code, self._home_code(), obj.fee)
        return str(val) if val is not None else None

    def get_net_amount_home(self, obj):
        val = convert_to_home(obj.asset.currency.code, self._home_code(), obj.net_amount)
        return str(val) if val is not None else None


class PositionSerializer(serializers.ModelSerializer):
    asset_ticker = serializers.CharField(source='asset.ticker')
    asset_name = serializers.CharField(source='asset.name')
    exchange_code = serializers.CharField(source='asset.exchange.code')
    asset_currency_code = serializers.CharField(source='asset.currency.code')
    available_quantity = serializers.SerializerMethodField()
    cost_basis = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    unrealized_pnl = serializers.SerializerMethodField()
    pnl_percent = serializers.SerializerMethodField()
    # Home-currency equivalents
    current_price_home = serializers.SerializerMethodField()
    current_value_home = serializers.SerializerMethodField()
    unrealized_pnl_home = serializers.SerializerMethodField()
    cost_basis_home = serializers.SerializerMethodField()
    avg_cost_home = serializers.SerializerMethodField()
    realized_pnl_home = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            'id', 'asset_ticker', 'asset_name', 'exchange_code', 'asset_currency_code',
            'quantity', 'pending_quantity', 'available_quantity',
            'average_cost', 'realized_pnl', 'cost_basis',
            'current_price', 'current_value', 'unrealized_pnl', 'pnl_percent',
            'current_price_home', 'current_value_home', 'unrealized_pnl_home',
            'cost_basis_home', 'avg_cost_home', 'realized_pnl_home',
        ]

    def _home_code(self):
        return self.context.get('home_currency_code', '')

    def _asset_code(self, obj):
        return obj.asset.currency.code

    def _cached_price(self, obj):
        # Cache per-object so get_latest_price() isn't called multiple times
        cache = self.context.setdefault('_price_cache', {})
        if obj.pk not in cache:
            cache[obj.pk] = obj.asset.get_latest_price()
        return cache[obj.pk]

    def get_available_quantity(self, obj):
        return str(obj.available_quantity)

    def get_cost_basis(self, obj):
        return str(obj.total_cost_basis)

    def get_current_price(self, obj):
        p = self._cached_price(obj)
        return str(p) if p is not None else None

    def get_current_value(self, obj):
        p = self._cached_price(obj)
        if p is None:
            return None
        return str(obj.quantity * p)

    def get_unrealized_pnl(self, obj):
        p = self._cached_price(obj)
        if p is None:
            return None
        pnl = obj.calculate_unrealized_pnl()
        return str(pnl) if pnl is not None else None

    def get_pnl_percent(self, obj):
        pnl = obj.calculate_unrealized_pnl()
        if pnl is not None and obj.total_cost_basis > 0:
            return float(pnl / obj.total_cost_basis * 100)
        return None

    def get_current_price_home(self, obj):
        val = convert_to_home(self._asset_code(obj), self._home_code(), self._cached_price(obj))
        return str(val) if val is not None else None

    def get_current_value_home(self, obj):
        p = self._cached_price(obj)
        if p is None:
            return None
        val = convert_to_home(self._asset_code(obj), self._home_code(), obj.quantity * p)
        return str(val) if val is not None else None

    def get_unrealized_pnl_home(self, obj):
        pnl = obj.calculate_unrealized_pnl()
        val = convert_to_home(self._asset_code(obj), self._home_code(), pnl)
        return str(val) if val is not None else None

    def get_cost_basis_home(self, obj):
        val = convert_to_home(self._asset_code(obj), self._home_code(), obj.total_cost_basis)
        return str(val) if val is not None else None

    def get_avg_cost_home(self, obj):
        val = convert_to_home(self._asset_code(obj), self._home_code(), obj.average_cost)
        return str(val) if val is not None else None

    def get_realized_pnl_home(self, obj):
        val = convert_to_home(self._asset_code(obj), self._home_code(), obj.realized_pnl)
        return str(val) if val is not None else None


class PortfolioSerializer(serializers.Serializer):
    """Wraps a list of enriched positions with portfolio totals."""
    home_currency = serializers.CharField()
    total_value = serializers.DecimalField(max_digits=20, decimal_places=2, coerce_to_string=True)
    total_cost = serializers.DecimalField(max_digits=20, decimal_places=2, coerce_to_string=True)
    total_pnl = serializers.DecimalField(max_digits=20, decimal_places=2, coerce_to_string=True, allow_null=True)
    pnl_percent = serializers.FloatField(allow_null=True)
    positions = PositionSerializer(many=True)
