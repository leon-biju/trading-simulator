import pytest

from apps.accounts.forms import SignUpForm


#1. Test email normalisation
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
    SignUpForm.clean_email() must always return a lowercased email since
    emails are case insensitive
    """
    
    form = SignUpForm()
    form.cleaned_data = {"email": raw}
    assert form.clean_email() == expected 