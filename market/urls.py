from django.urls import path
from . import views_ui, views_api

urlpatterns = [
    # Market overview and browsing
    path('', views_ui.market_overview_view, name='market_overview'),
    path('exchange/<str:exchange_code>/', views_ui.exchange_detail_view, name='exchange_detail'),
    
    # Asset detail page
    path('assets/<str:exchange_code>/<str:asset_symbol>/', views_ui.asset_detail_view, name='asset_detail'),
        
    # Chart data API endpoints
    path('data/assets/<str:exchange_code>/<str:asset_symbol>/', views_api.asset_performance_chart_data_view, name='asset_performance_chart_data'),
]