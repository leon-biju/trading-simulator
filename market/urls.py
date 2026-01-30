from django.urls import path
from . import views

urlpatterns = [
    # Market overview and browsing
    path('', views.market_overview_view, name='market_overview'),
    path('exchange/<str:exchange_code>/', views.exchange_detail_view, name='exchange_detail'),
    
    # Stock detail page (renamed from stock_performance)
    path('stocks/<str:exchange_code>/<str:stock_symbol>/', views.asset_detail_view, name='stock_detail'),
    
    # Legacy route for backwards compatibility TODO: Remove
    path('stocks/<str:exchange_code>/<str:asset_symbol>/performance/', views.asset_performance_view, name='stock_performance'),
    
    # Chart data API endpoints
    path('data/stocks/<str:exchange_code>/<str:asset_symbol>/', views.asset_performance_chart_data_view, name='stock_performance_chart_data'),
]