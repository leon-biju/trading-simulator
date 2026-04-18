from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from market.models import Currency

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, label='Confirm password', trim_whitespace=False)
    home_currency = serializers.CharField(max_length=3)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        return value

    def validate_home_currency(self, value):
        try:
            return Currency.objects.get(code=value.upper())
        except Currency.DoesNotExist:
            raise serializers.ValidationError(f'Currency "{value}" does not exist.')

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        validate_password(data['password'])
        return data

    def create(self, validated_data):
        home_currency = validated_data.pop('home_currency')
        validated_data.pop('password2')

        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
        )
        user.set_password(validated_data['password'])
        # Must be set before save() so the post_save signal can forward it to Profile
        user._home_currency = home_currency  # type: ignore[attr-defined]
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    home_currency = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    total_cash = serializers.SerializerMethodField()
    leaderboard_visible = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'home_currency', 'display_name', 'total_cash', 'leaderboard_visible']

    def get_home_currency(self, obj):
        return obj.home_currency.code

    def get_display_name(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.display_name if profile else ''

    def get_total_cash(self, obj):
        return str(obj.total_cash)

    def get_leaderboard_visible(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.leaderboard_visible if profile else True
