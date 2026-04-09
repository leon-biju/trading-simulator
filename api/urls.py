from django.urls import path

from api.views.auth import (
    CookieTokenBlacklistView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    RegisterView,
)
from api.views.market import (
    AssetDetailView,
    ChartDataView,
    ExchangeDetailView,
    ExchangeListView,
    FxRatesView,
)
from api.views.trading import (
    CancelOrderView,
    OrderListCreateView,
    PortfolioHistoryView,
    PortfolioView,
    PositionView,
    TradeListView,
)
from api.views.users import CurrentUserView
from api.views.wallets import FxTransferView, WalletDetailView, WalletListView

urlpatterns = [
    # Auth
    path('auth/token/', CookieTokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', CookieTokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/blacklist/', CookieTokenBlacklistView.as_view(), name='api_token_blacklist'),
    path('auth/register/', RegisterView.as_view(), name='api_register'),

    # User
    path('users/me/', CurrentUserView.as_view(), name='api_me'),

    # Wallets
    path('wallets/', WalletListView.as_view(), name='api_wallets'),
    path('wallets/fx-transfer/', FxTransferView.as_view(), name='api_fx_transfer'),
    path('wallets/fx-rates/', FxRatesView.as_view(), name='api_fx_rates'),
    path('wallets/<str:currency_code>/', WalletDetailView.as_view(), name='api_wallet_detail'),

    # Market
    path('market/exchanges/', ExchangeListView.as_view(), name='api_exchanges'),
    path('market/exchanges/<str:exchange_code>/', ExchangeDetailView.as_view(), name='api_exchange_detail'),
    path('market/assets/<str:exchange_code>/<str:ticker>/', AssetDetailView.as_view(), name='api_asset_detail'),
    path('market/data/<str:exchange_code>/<str:ticker>/', ChartDataView.as_view(), name='api_chart_data'),

    # Trading
    path('trading/portfolio/', PortfolioView.as_view(), name='api_portfolio'),
    path('trading/portfolio/history/', PortfolioHistoryView.as_view(), name='api_portfolio_history'),
    path('trading/orders/', OrderListCreateView.as_view(), name='api_orders'),
    path('trading/orders/<int:order_id>/cancel/', CancelOrderView.as_view(), name='api_cancel_order'),
    path('trading/trades/', TradeListView.as_view(), name='api_trades'),
    path('trading/position/<str:exchange_code>/<str:ticker>/', PositionView.as_view(), name='api_position'),
]
