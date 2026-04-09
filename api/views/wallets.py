from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.pagination import StandardPagination
from api.serializers.wallets import (
    FxTransferInputSerializer,
    TransactionSerializer,
    WalletSerializer,
)
from wallets.models import Transaction, Wallet
from wallets.services import perform_fx_transfer


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class WalletListView(APIView):
    def get(self, request):
        wallets = Wallet.objects.filter(user_id=request.user.id).select_related('currency')
        serializer = WalletSerializer(wallets, many=True)
        return Response(serializer.data)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
class WalletDetailView(APIView):
    def get(self, request, currency_code):
        try:
            wallet = Wallet.objects.select_related('currency').get(
                user_id=request.user.id,
                currency__code=currency_code.upper(),
            )
        except Wallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)

        transactions = (
            Transaction.objects.filter(wallet=wallet)
            .order_by('-timestamp')
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(transactions, request)
        tx_data = TransactionSerializer(page, many=True).data

        wallet_data = WalletSerializer(wallet).data
        paginated = paginator.get_paginated_response(tx_data).data
        wallet_data['transactions'] = paginated
        return Response(wallet_data)


@method_decorator(ratelimit(key='user', rate='10/m', block=True), name='post')
class FxTransferView(APIView):
    def post(self, request):
        serializer = FxTransferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer = perform_fx_transfer(
            user_id=request.user.id,
            from_wallet_currency_code=data['from_currency'].upper(),
            to_wallet_currency_code=data['to_currency'].upper(),
            from_amount=data.get('from_amount'),
            to_amount=data.get('to_amount'),
        )

        return Response({
            'from_amount': str(transfer.from_amount),
            'to_amount': str(transfer.to_amount),
            'exchange_rate': str(transfer.exchange_rate),
            'from_currency': data['from_currency'].upper(),
            'to_currency': data['to_currency'].upper(),
        }, status=status.HTTP_201_CREATED)
