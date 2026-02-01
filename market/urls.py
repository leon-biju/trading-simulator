from django.urls import path
from . import views

urlpatterns = [
    # Market overview and browsing
    path('', views.market_overview_view, name='market_overview'),
    path('exchange/<str:exchange_code>/', views.exchange_detail_view, name='exchange_detail'),
    
    # Asset detail page
    path('assets/<str:exchange_code>/<str:asset_symbol>/', views.asset_detail_view, name='asset_detail'),
        
    # Chart data API endpoints
    path('data/assets/<str:exchange_code>/<str:asset_symbol>/', views.asset_performance_chart_data_view, name='asset_performance_chart_data'),
]