from decimal import Decimal

from rest_framework import serializers
from wallets.models import Transaction, Wallet


class TransactionSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source='get_source_display')

    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'balance_after', 'source', 'source_display', 'timestamp', 'description']


class WalletSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code')
    currency_name = serializers.CharField(source='currency.name')
    available_balance = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['currency_code', 'currency_name', 'balance', 'pending_balance', 'available_balance']

    def get_available_balance(self, obj):
        return str(obj.available_balance)


class FxTransferInputSerializer(serializers.Serializer):
    from_currency = serializers.CharField(max_length=3)
    to_currency = serializers.CharField(max_length=3)
    to_amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.01'))
    from_amount = serializers.DecimalField(max_digits=20, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.01'))

    def validate(self, data):
        if not data.get('to_amount') and not data.get('from_amount'):
            raise serializers.ValidationError('Provide either to_amount or from_amount.')
        if data.get('to_amount') and data.get('from_amount'):
            raise serializers.ValidationError('Provide only one of to_amount or from_amount.')
        if data.get('from_currency') == data.get('to_currency'):
            raise serializers.ValidationError('Cannot transfer between same currency wallets.')
        return data
