from django.urls import path
from . import views

app_name = 'wallets'

urlpatterns = [
    path('<str:currency>/', views.wallet_detail, name='wallet_detail'),
]
