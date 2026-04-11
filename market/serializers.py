from rest_framework import serializers
from market.models import Asset, Exchange, FXRate


class ExchangeSerializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()
    hours_until_open = serializers.SerializerMethodField()

    class Meta:
        model = Exchange
        fields = ['name', 'code', 'timezone', 'open_time', 'close_time', 'is_open', 'hours_until_open']

    def get_is_open(self, obj):
        return obj.is_currently_open()

    def get_hours_until_open(self, obj):
        if obj.is_currently_open():
            return None
        return obj.hours_until_open()


class AssetListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for asset lists (market overview, exchange detail)."""
    currency_code = serializers.CharField(source='currency.code')
    current_price = serializers.SerializerMethodField()
    exchange_code = serializers.CharField(source='exchange.code')

    class Meta:
        model = Asset
        fields = ['ticker', 'name', 'asset_type', 'currency_code', 'exchange_code', 'is_active', 'current_price']

    def get_current_price(self, obj):
        price = obj.get_latest_price()
        return str(price) if price is not None else None


class ExchangeListSerializer(ExchangeSerializer):
    assets = AssetListSerializer(many=True, read_only=True)
    asset_count = serializers.SerializerMethodField()

    class Meta(ExchangeSerializer.Meta):
        fields = ExchangeSerializer.Meta.fields + ['assets', 'asset_count']

    def get_asset_count(self, obj):
        # Use prefetched queryset if available
        assets = self.context.get('prefetched_assets', {}).get(obj.pk, [])
        return len(assets)


class AssetDetailSerializer(serializers.ModelSerializer):
    """Full asset serializer for the asset detail page."""
    currency_code = serializers.CharField(source='currency.code')
    exchange_code = serializers.CharField(source='exchange.code')
    exchange_name = serializers.CharField(source='exchange.name')
    exchange_open_time = serializers.TimeField(source='exchange.open_time')
    exchange_close_time = serializers.TimeField(source='exchange.close_time')
    exchange_timezone = serializers.CharField(source='exchange.timezone')
    is_exchange_open = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    user_wallet = serializers.SerializerMethodField()
    user_position = serializers.SerializerMethodField()
    pending_orders = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            'ticker', 'name', 'asset_type',
            'currency_code', 'exchange_code', 'exchange_name',
            'exchange_open_time', 'exchange_close_time', 'exchange_timezone',
            'is_exchange_open', 'is_active', 'current_price',
            'user_wallet', 'user_position', 'pending_orders',
        ]

    def get_is_exchange_open(self, obj):
        return obj.exchange.is_currently_open()

    def get_current_price(self, obj):
        price = obj.get_latest_price()
        return str(price) if price is not None else None

    def get_user_wallet(self, obj):
        wallet = self.context.get('wallet')
        if wallet is None:
            return None
        return {
            'balance': str(wallet.balance),
            'available_balance': str(wallet.available_balance),
            'pending_balance': str(wallet.pending_balance),
            'currency_code': wallet.currency.code,
        }

    def get_user_position(self, obj):
        position = self.context.get('position')
        if position is None:
            return {'has_position': False}
        return {
            'has_position': True,
            'quantity': str(position.quantity),
            'available_quantity': str(position.available_quantity),
            'average_cost': str(position.average_cost),
            'pending_quantity': str(position.pending_quantity),
        }

    def get_pending_orders(self, obj):
        orders = self.context.get('pending_orders', [])
        return [
            {
                'id': o.id,
                'side': o.side,
                'order_type': o.order_type,
                'quantity': str(o.quantity),
                'limit_price': str(o.limit_price) if o.limit_price else None,
                'status': o.status,
                'created_at': o.created_at.isoformat(),
            }
            for o in orders
        ]


class FxRateSerializer(serializers.ModelSerializer):
    from_currency = serializers.CharField(source='base_currency.code')
    to_currency = serializers.CharField(source='target_currency.code')

    class Meta:
        model = FXRate
        fields = ['from_currency', 'to_currency', 'rate', 'last_updated']
