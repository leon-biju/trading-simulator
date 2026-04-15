import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.models import PasswordResetOTP
from accounts.serializers import RegisterSerializer, UserSerializer

User = get_user_model()

COOKIE_NAME = 'refresh_token'
COOKIE_MAX_AGE = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())


def _set_refresh_cookie(response, refresh_token_str):
    response.set_cookie(
        COOKIE_NAME,
        refresh_token_str,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        path='/',
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(COOKIE_NAME, path='/')


@method_decorator(ratelimit(key='ip', rate='10/m', block=True), name='post')
class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Login: validates credentials, returns access token in body,
    sets refresh token as httpOnly cookie.
    """

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = serializer.validated_data['refresh']
        access = serializer.validated_data['access']

        response = Response({'access': access}, status=status.HTTP_200_OK)
        _set_refresh_cookie(response, refresh)
        return response


@method_decorator(ratelimit(key='ip', rate='30/m', block=True), name='post')
class CookieTokenRefreshView(TokenRefreshView):
    """
    Silent refresh: reads refresh token from httpOnly cookie,
    returns new access token in body and rotates cookie.
    """

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(COOKIE_NAME)
        if not refresh_token:
            return Response({'error': 'No refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken):
            response = Response({'error': 'Token expired or invalid'}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        access = serializer.validated_data['access']
        response = Response({'access': access}, status=status.HTTP_200_OK)

        # If rotation is enabled, a new refresh token is issued — update the cookie
        new_refresh = serializer.validated_data.get('refresh')
        if new_refresh:
            _set_refresh_cookie(response, new_refresh)

        return response


class CookieTokenBlacklistView(APIView):
    """
    Logout: blacklists the refresh token from the cookie and clears it.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(COOKIE_NAME)
        response = Response({'detail': 'Logged out'}, status=status.HTTP_200_OK)
        _clear_refresh_cookie(response)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except (TokenError, InvalidToken):
                pass  # Already invalid — that's fine

        return response


@method_decorator(ratelimit(key='ip', rate='5/h', block=True), name='post')
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Issue tokens immediately so user is logged in after registration
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        response = Response(
            {'access': access, 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


@method_decorator(ratelimit(key='ip', rate='5/h', block=True), name='post')
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
            fail_silently=True,
        )

        return response


@method_decorator(ratelimit(key='ip', rate='10/h', block=True), name='post')
class PasswordResetVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        otp = request.data.get('otp', '').strip()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        record = (
            PasswordResetOTP.objects
            .filter(user=user, used=False)
            .order_by('-created_at')
            .first()
        )

        if not record or not record.is_valid() or not check_password(otp, record.otp_hash):
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Code verified.'}, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='ip', rate='10/h', block=True), name='post')
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
            return Response({'error': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        record = (
            PasswordResetOTP.objects
            .filter(user=user, used=False)
            .order_by('-created_at')
            .first()
        )

        if not record or not record.is_valid() or not check_password(otp, record.otp_hash):
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
