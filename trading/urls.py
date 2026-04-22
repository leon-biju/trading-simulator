from django.urls import path

from trading.views import (
    AnalyticsActivityView,
    AnalyticsAllocationView,
    AnalyticsStatsView,
    CancelOrderView,
    OrderListCreateView,
    PortfolioHistoryView,
    PortfolioView,
    PositionView,
    TradeListView,
)

urlpatterns = [
    path('trading/portfolio/', PortfolioView.as_view(), name='api_portfolio'),
    path('trading/portfolio/history/', PortfolioHistoryView.as_view(), name='api_portfolio_history'),
    path('trading/orders/', OrderListCreateView.as_view(), name='api_orders'),
    path('trading/orders/<int:order_id>/cancel/', CancelOrderView.as_view(), name='api_cancel_order'),
    path('trading/trades/', TradeListView.as_view(), name='api_trades'),
    path('trading/position/<str:exchange_code>/<str:ticker>/', PositionView.as_view(), name='api_position'),
    path('trading/analytics/stats/', AnalyticsStatsView.as_view(), name='api_analytics_stats'),
    path('trading/analytics/allocation/', AnalyticsAllocationView.as_view(), name='api_analytics_allocation'),
    path('trading/analytics/activity/', AnalyticsActivityView.as_view(), name='api_analytics_activity'),
]
