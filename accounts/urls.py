from django.urls import path

from accounts.views import (
    CurrentUserView,
    LeaderboardView,
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    RegisterView,
    WatchlistView,
    WatchlistDetailView,
)

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='api_login'),
    path('auth/logout/', LogoutView.as_view(), name='api_logout'),
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='api_password_reset'),
    path('auth/password/reset/verify/', PasswordResetVerifyView.as_view(), name='api_password_reset_verify'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='api_password_reset_confirm'),
    path('auth/password/change/', PasswordChangeView.as_view(), name='api_password_change'),
    path('users/me/', CurrentUserView.as_view(), name='api_me'),
    path('users/watchlist/', WatchlistView.as_view(), name='api_watchlist'),
    path('users/watchlist/<str:exchange_code>/<str:ticker>/', WatchlistDetailView.as_view(), name='api_watchlist_detail'),
    path('leaderboard/', LeaderboardView.as_view(), name='api_leaderboard'),
]
