# mypy: disable-error-code=no-untyped-def

import pytest

from accounts.serializers import RegisterSerializer


# 1. Test email normalisation
@pytest.mark.django_db
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("FOO@EXAMPLE.COM", "foo@example.com"),
        ("MiXeD@Case.Org", "mixed@case.org"),
        ("already.lower@ed.net", "already.lower@ed.net"),
    ],
)
def test_normalised_email(raw, expected):
    """
    RegisterSerializer.validate_email() must always return a lowercased email
    since emails are case insensitive.
    """
    s = RegisterSerializer()
    s.initial_data = {}  # type: ignore[attr-defined]
    result = s.validate_email(raw)
    assert result == expected
