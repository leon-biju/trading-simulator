from django.urls import path
from . import views_ui, views_api

urlpatterns = [
    # Order management
    path('order/<int:order_id>/cancel/', views_ui.cancel_order_view, name='cancel_order'),
    # Order placement
    path(
        'order/<str:exchange_code>/<str:asset_symbol>/', 
        views_ui.place_order_view, 
        name='place_order'
    ),
        
    # History views
    path('orders/', views_ui.order_history_view, name='order_history'),
    path('trades/', views_ui.trade_history_view, name='trade_history'),
    
    # Portfolio
    path('portfolio/', views_ui.portfolio_view, name='portfolio'),
    
    # API endpoints for dynamic form updates
    path(
        'api/position/<str:exchange_code>/<str:asset_symbol>/', 
        views_api.get_position_for_stock, 
        name='api_get_position'
    ),
    path(
        'api/wallet/<str:currency_code>/', 
        views_api.get_wallet_balance, 
        name='api_get_wallet'
    ),
    path(
        'api/portfolio-history/',
        views_api.portfolio_history_api,
        name='api_portfolio_history'
    ),
]
