from django.urls import path

from wallets.views import FxTransferView, WalletDetailView, WalletListView

urlpatterns = [
    path('wallets/', WalletListView.as_view(), name='api_wallets'),
    path('wallets/fx-transfer/', FxTransferView.as_view(), name='api_fx_transfer'),
    path('wallets/<str:currency_code>/', WalletDetailView.as_view(), name='api_wallet_detail'),
]
