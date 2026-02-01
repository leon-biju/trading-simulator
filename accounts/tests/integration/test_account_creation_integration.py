# mypy: disable-error-code=no-untyped-def

import pytest
from accounts.forms import SignUpForm, LoginForm
from django.contrib.auth import get_user_model


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
    form = SignUpForm(data={
        "username": "testuser",
        "email": "testuser@example.com",
        "password1": password,
        "password2": password,
    })
    assert form.is_valid() == expected



# 2. Reject mismatched passwords
@pytest.mark.parametrize(
    "password1, password2, expected", [
        ("StrongV3ryStrongPasswd!", "StrongV3ryStrongPasswd! ", False),
        ("StrongV3ryStrongPasswd!", "StrongVeryStrongPasswd!", False),
        ("MatchedPasswd!223", "MatchedPasswd!223", True),
    ]
)
def test_password_confirmation(password1, password2, expected, market_data):
    form = SignUpForm(data={
        "username": "testuser",
        "email": "testuser@example.com",
        "password1": password1,
        "password2": password2,
    })
    assert form.is_valid() == expected



# 3. Cannot create an account with an existing username
def test_cannot_create_account_with_existing_username(market_data):
    User = get_user_model()

    # Create initial user
    User.objects.create_user(username="test_user", email="test_first@example.com", password="StrongV3ryStrongPasswd!")

    # Attempt to create another user with same username
    form = SignUpForm(data={
        "username": "test_user",
        "email": "test_second@example.com",
        "password1": "AnotherStrongPasswd!123",
        "password2": "AnotherStrongPasswd!123",
    })
    assert not form.is_valid()
    assert "username" in form.errors



# 4. Cannot create an account with an existing email
def test_cannot_create_account_with_existing_email(market_data):
    User = get_user_model()

    # Create initial user
    User.objects.create_user(username="test_user1", email="testemail@example.com", password="StrongV3ryStrongPasswd!")

    # Attempt to create another user with same email
    form = SignUpForm(data={
        "username": "test_user2",
        "email": "testemail@example.com",
        "password1": "AnotherStrongPasswd!123",
        "password2": "AnotherStrongPasswd!123",
    })
    assert not form.is_valid()
    assert "email" in form.errors



# 5. Passwords are stored hashed NOT plaintext
def test_password_is_hashed(market_data):
    raw_password = "StrongV3ryStrongPasswd!"
    form = SignUpForm(data={
        "username": "test_user_hashed",
        "email": "testemail_hashed@example.com",
        "password1": raw_password,
        "password2": raw_password,
    })
    assert form.is_valid()
    user = form.save()

    assert user.password != raw_password

    # The user can authenticate with raw password
    assert user.check_password(raw_password)