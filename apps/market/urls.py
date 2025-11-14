from django.urls import path
from . import views

urlpatterns = [
    path('stocks/<str:exchange_code>/<str:asset_symbol>/', views.stock_performance_view, name='stock_performance'),
    path('currency-assets/<str:asset_symbol>/', views.currency_asset_performance_view, name='currency_asset_performance'),
    path('data/stocks/<str:exchange_code>/<str:asset_symbol>/', views.stock_performance_chart_data_view, name='stock_performance_chart_data'),
    path('data/currency-assets/<str:asset_symbol>/', views.currency_asset_performance_chart_data_view, name='currency_asset_performance_chart_data'),
]