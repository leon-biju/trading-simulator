from django.urls import path

from market.views import (
    AssetDetailView,
    ChartDataView,
    ExchangeDetailView,
    ExchangeListView,
    FxRatesView,
    MarketMoversView,
)

urlpatterns = [
    path('market/movers/', MarketMoversView.as_view(), name='api_market_movers'),
    path('market/exchanges/', ExchangeListView.as_view(), name='api_exchanges'),
    path('market/exchanges/<str:exchange_code>/', ExchangeDetailView.as_view(), name='api_exchange_detail'),
    path('market/assets/<str:exchange_code>/<str:ticker>/', AssetDetailView.as_view(), name='api_asset_detail'),
    path('market/data/<str:exchange_code>/<str:ticker>/', ChartDataView.as_view(), name='api_chart_data'),
    path('wallets/fx-rates/', FxRatesView.as_view(), name='api_fx_rates'),
]
