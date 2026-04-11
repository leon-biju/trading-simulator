from django.urls import path

from accounts.views import (
    CookieTokenBlacklistView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CurrentUserView,
    RegisterView,
)

urlpatterns = [
    path('auth/token/', CookieTokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', CookieTokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/blacklist/', CookieTokenBlacklistView.as_view(), name='api_token_blacklist'),
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('users/me/', CurrentUserView.as_view(), name='api_me'),
]
