from django.urls import path
from . import views

urlpatterns = [
    # Order placement
    path(
        'order/<str:exchange_code>/<str:stock_symbol>/', 
        views.place_order_view, 
        name='place_order'
    ),
    
    # Order management
    path('order/<int:order_id>/cancel/', views.cancel_order_view, name='cancel_order'), # This is horrible why would you do this. TODO make it not stupid. smh treating a POST like you do a GET request no forms or anything.
    
    # History views
    path('orders/', views.order_history_view, name='order_history'),
    path('trades/', views.trade_history_view, name='trade_history'),
    
    # Portfolio
    path('portfolio/', views.portfolio_view, name='portfolio'),
    
    # API endpoints for dynamic form updates
    path(
        'api/position/<str:exchange_code>/<str:stock_symbol>/', 
        views.get_position_for_stock, 
        name='api_get_position'
    ),
    path(
        'api/wallet/<str:currency_code>/', 
        views.get_wallet_balance, 
        name='api_get_wallet'
    ),
]
