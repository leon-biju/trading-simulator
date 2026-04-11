from django.urls import path

from accounts.views import (
    CookieTokenBlacklistView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CurrentUserView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RegisterView,
)

urlpatterns = [
    path('auth/token/', CookieTokenObtainPairView.as_view(), name='api_token_obtain'),
    path('auth/token/refresh/', CookieTokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/token/blacklist/', CookieTokenBlacklistView.as_view(), name='api_token_blacklist'),
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='api_password_reset'),
    path('auth/password/reset/verify/', PasswordResetVerifyView.as_view(), name='api_password_reset_verify'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='api_password_reset_confirm'),
    path('users/me/', CurrentUserView.as_view(), name='api_me'),
]
