import datetime
import secrets
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db.models import OuterRef, Subquery, ExpressionWrapper, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from config.ratelimit import client_ip_key
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import PasswordResetOTP, WatchlistItem
from accounts.serializers import RegisterSerializer, UserSerializer
from market.models import Asset, PriceCandle
from trading.models import PortfolioSnapshot

User = get_user_model()


@method_decorator(ratelimit(key=client_ip_key, rate='10/m', block=True), name='post')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({'detail': 'Logged out'})


@method_decorator(ratelimit(key=client_ip_key, rate='5/h', block=True), name='post')
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        profile = request.user.profile
        errors = {}

        if 'display_name' in request.data:
            display_name = request.data['display_name']
            if len(display_name) > 100:
                errors['display_name'] = 'Max 100 characters.'
            else:
                profile.display_name = display_name

        if 'home_currency' in request.data:
            from market.models import Currency
            code = request.data['home_currency']
            try:
                profile.home_currency = Currency.objects.get(code=code.upper())
            except Currency.DoesNotExist:
                errors['home_currency'] = f'Currency "{code}" does not exist.'

        if 'leaderboard_visible' in request.data:
            value = request.data['leaderboard_visible']
            if not isinstance(value, bool):
                errors['leaderboard_visible'] = 'Must be a boolean.'
            else:
                profile.leaderboard_visible = value

        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        profile.save()
        return Response(UserSerializer(request.user).data)


@method_decorator(ratelimit(key='user', rate='10/h', block=True), name='post')
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')
        new_password2 = request.data.get('new_password2', '')

        if not request.user.check_password(current_password):
            return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password2:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=request.user)
        except Exception as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()
        return Response({'detail': 'Password changed.'}, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key=client_ip_key, rate='5/h', block=True), name='post')
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        # Always return 200 — never confirm whether an email exists
        response = Response(
            {'detail': 'If that email exists, a reset code has been sent.'},
            status=status.HTTP_200_OK,
        )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return response

        otp = f"{secrets.randbelow(1_000_000):06d}"
        PasswordResetOTP.objects.create(user=user, otp_hash=make_password(otp))

        try:
            send_mail(
                subject='Your password reset code',
                message=(
                    f'Hi {user.username},\n\n'
                    f'Your password reset code is: {otp}\n\n'
                    f'It expires in 10 minutes. '
                    f'If you did not request this, you can ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            logging.error(f"Failed to send password reset email to {user.email}: {e}")

        return response


@method_decorator(ratelimit(key=client_ip_key, rate='10/h', block=True), name='post')
class PasswordResetVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        otp = request.data.get('otp', '').strip()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        record = (
            PasswordResetOTP.objects
            .filter(user=user, used=False)
            .order_by('-created_at')
            .first()
        )

        if not record or not record.is_valid():
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(otp, record.otp_hash):
            record.failed_attempts += 1
            record.save(update_fields=['failed_attempts'])
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Code verified.'}, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key=client_ip_key, rate='10/h', block=True), name='post')
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        otp = request.data.get('otp', '').strip()
        new_password = request.data.get('new_password', '')
        new_password2 = request.data.get('new_password2', '')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        record = (
            PasswordResetOTP.objects
            .filter(user=user, used=False)
            .order_by('-created_at')
            .first()
        )

        if not record or not record.is_valid():
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        if not check_password(otp, record.otp_hash):
            record.failed_attempts += 1
            record.save(update_fields=['failed_attempts'])
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password2:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=user)
        except Exception as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        record.used = True
        record.save(update_fields=['used'])

        user.set_password(new_password)
        user.save()

        return Response({'detail': 'Password has been reset.'}, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='get')
@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='post')
class WatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        asset_ids = WatchlistItem.objects.filter(
            user=request.user,
        ).values_list('asset_id', flat=True)

        now = timezone.now()
        cutoff_24h = now - datetime.timedelta(hours=24)

        latest_price_sq = Subquery(
            PriceCandle.objects.filter(
                asset=OuterRef('pk'),
            ).order_by('-start_at').values('close_price')[:1]
        )
        price_24h_ago_sq = Subquery(
            PriceCandle.objects.filter(
                asset=OuterRef('pk'),
                start_at__lte=cutoff_24h,
            ).order_by('-start_at').values('close_price')[:1]
        )

        assets = (
            Asset.objects.filter(pk__in=asset_ids)
            .select_related('currency', 'exchange')
            .annotate(latest_price=latest_price_sq, price_24h_ago=price_24h_ago_sq)
        )

        result = []
        for asset in assets:
            change_pct = None
            if asset.latest_price and asset.price_24h_ago:
                past = float(asset.price_24h_ago)
                if past != 0:
                    change_pct = round((float(asset.latest_price) - past) / past * 100, 2)
            result.append({
                'ticker':        asset.ticker,
                'name':          asset.name,
                'exchange_code': asset.exchange.code,
                'currency_code': asset.currency.code,
                'current_price': str(asset.latest_price) if asset.latest_price else None,
                'change_pct':    change_pct,
            })
        return Response(result)

    def post(self, request):
        exchange_code = request.data.get('exchange_code')
        ticker = request.data.get('ticker')
        if not exchange_code or not ticker:
            return Response(
                {'error': 'exchange_code and ticker are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            asset = Asset.objects.get(exchange__code=exchange_code, ticker=ticker)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found'}, status=status.HTTP_404_NOT_FOUND)

        WatchlistItem.objects.get_or_create(user=request.user, asset=asset)
        return Response(status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='user', rate='60/m', block=True), name='delete')
class WatchlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, exchange_code, ticker):
        deleted, _ = WatchlistItem.objects.filter(
            user=request.user,
            asset__exchange__code=exchange_code,
            asset__ticker=ticker,
        ).delete()
        if not deleted:
            return Response({'error': 'Not in watchlist'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


_VALID_PERIODS = {'today', 'week', 'month', 'year'}
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100


def _period_start(period: str) -> datetime.date:
    today = timezone.now().date()
    if period == 'today':
        return today
    if period == 'week':
        return today - datetime.timedelta(days=today.weekday())
    if period == 'month':
        return today.replace(day=1)
    # year
    return today.replace(month=1, day=1)


class LeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        period = request.query_params.get('period', 'week')
        if period not in _VALID_PERIODS:
            return Response({'error': f'period must be one of {sorted(_VALID_PERIODS)}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = min(int(request.query_params.get('limit', _DEFAULT_LIMIT)), _MAX_LIMIT)
        except ValueError:
            return Response({'error': 'limit must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        period_start = _period_start(period)

        latest_snap = PortfolioSnapshot.objects.filter(
            user=OuterRef('pk')
        ).order_by('-date').values('total_portfolio_value')[:1]

        at_period_start = PortfolioSnapshot.objects.filter(
            user=OuterRef('pk'),
            date__lte=period_start,
        ).order_by('-date').values('total_portfolio_value')[:1]

        earliest_snap = PortfolioSnapshot.objects.filter(
            user=OuterRef('pk')
        ).order_by('date').values('total_portfolio_value')[:1]

        users = (
            User.objects.filter(
                profile__leaderboard_visible=True,
                portfolio_snapshots__isnull=False,
            )
            .distinct()
            .annotate(
                current_total=Subquery(latest_snap),
                start_total=Coalesce(
                    Subquery(at_period_start),
                    Subquery(earliest_snap),
                ),
            )
            .filter(
                current_total__isnull=False,
                start_total__isnull=False,
                start_total__gt=0,
            )
            .annotate(
                return_abs=ExpressionWrapper(
                    F('current_total') - F('start_total'),
                    output_field=DecimalField(max_digits=20, decimal_places=2),
                ),
                return_pct=ExpressionWrapper(
                    (F('current_total') - F('start_total')) / F('start_total') * 100,
                    output_field=DecimalField(max_digits=20, decimal_places=4),
                ),
            )
            .order_by('-return_pct')[:limit]
        )

        data = [
            {
                'rank': i + 1,
                'username': u.username,
                'current_total': str(u.current_total),
                'return_abs': str(u.return_abs),
                'return_pct': str(round(u.return_pct, 4)),
            }
            for i, u in enumerate(users)
        ]
        return Response(data)
