from django.urls import path

from accounts.views import (
    CookieTokenBlacklistView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CurrentUserView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RegisterView,
    WatchlistView,
    WatchlistDetailView,
)

urlpatterns = [
    path('auth/token/', CookieTokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', CookieTokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/blacklist/', CookieTokenBlacklistView.as_view(), name='api_token_blacklist'),
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='api_password_reset'),
    path('auth/password/reset/verify/', PasswordResetVerifyView.as_view(), name='api_password_reset_verify'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='api_password_reset_confirm'),
    path('auth/password/change/', PasswordChangeView.as_view(), name='api_password_change'),
    path('users/me/', CurrentUserView.as_view(), name='api_me'),
    path('users/watchlist/', WatchlistView.as_view(), name='api_watchlist'),
    path('users/watchlist/<str:exchange_code>/<str:ticker>/', WatchlistDetailView.as_view(), name='api_watchlist_detail'),
]
