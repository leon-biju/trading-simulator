from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('market.urls')),
    path('api/', include('trading.urls')),
    path('api/', include('wallets.urls')),
]
