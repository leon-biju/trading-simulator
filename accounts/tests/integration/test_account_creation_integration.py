# mypy: disable-error-code=no-untyped-def

import pytest
from django.contrib.auth import get_user_model

from accounts.serializers import RegisterSerializer


def _serializer(data):
    return RegisterSerializer(data=data)


# 1. Reject weak passwords
@pytest.mark.parametrize(
    "password, expected", [
        ("12345", False),
        ("short", False),
        ("password", False),
        ("qwerty", False),
        ("letmein", False),
        ("Password1!", False),
        ("StrongV3ryStrongPasswd!", True),
    ]
)
def test_weak_password_reject(password, expected, market_data):
    s = _serializer({
        "username": "testuser",
        "email": "testuser@example.com",
        "password": password,
        "password2": password,
        "home_currency": market_data["currencies"]["USD"].code,
    })
    assert s.is_valid() == expected


# 2. Reject mismatched passwords
@pytest.mark.parametrize(
    "password1, password2, expected", [
        ("StrongV3ryStrongPasswd!", "StrongV3ryStrongPasswd! ", False),
        ("StrongV3ryStrongPasswd!", "StrongVeryStrongPasswd!", False),
        ("MatchedPasswd!223", "MatchedPasswd!223", True),
    ]
)
def test_password_confirmation(password1, password2, expected, market_data):
    s = _serializer({
        "username": "testuser",
        "email": "testuser@example.com",
        "password": password1,
        "password2": password2,
        "home_currency": market_data["currencies"]["USD"].code,
    })
    assert s.is_valid() == expected


# 3. Cannot create an account with an existing username
def test_cannot_create_account_with_existing_username(market_data):
    User = get_user_model()
    User.objects.create_user(username="test_user", email="test_first@example.com", password="StrongV3ryStrongPasswd!")

    s = _serializer({
        "username": "test_user",
        "email": "test_second@example.com",
        "password": "AnotherStrongPasswd!123",
        "password2": "AnotherStrongPasswd!123",
        "home_currency": market_data["currencies"]["USD"].code,
    })
    assert not s.is_valid()
    assert "username" in s.errors


# 4. Cannot create an account with an existing email
def test_cannot_create_account_with_existing_email(market_data):
    User = get_user_model()
    User.objects.create_user(username="test_user1", email="testemail@example.com", password="StrongV3ryStrongPasswd!")

    s = _serializer({
        "username": "test_user2",
        "email": "testemail@example.com",
        "password": "AnotherStrongPasswd!123",
        "password2": "AnotherStrongPasswd!123",
        "home_currency": market_data["currencies"]["USD"].code,
    })
    assert not s.is_valid()
    assert "email" in s.errors


# 5. Passwords are stored hashed NOT plaintext
def test_password_is_hashed(market_data):
    raw_password = "StrongV3ryStrongPasswd!"
    s = _serializer({
        "username": "test_user_hashed",
        "email": "testemail_hashed@example.com",
        "password": raw_password,
        "password2": raw_password,
        "home_currency": market_data["currencies"]["USD"].code,
    })
    assert s.is_valid(), s.errors
    user = s.save()

    assert user.password != raw_password
    assert user.check_password(raw_password)
