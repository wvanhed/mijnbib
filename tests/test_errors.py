import pytest

from mijnbib.errors import (
    AuthenticationError,
    IncompatibleSourceError,
    UnexpectedLoginRedirectError,
)


def test_incompatiblesourceerror():
    with pytest.raises(IncompatibleSourceError) as e:
        raise IncompatibleSourceError("message", "some source text")
    assert str(e.value) == "message"
    assert e.value.html_body == "some source text"


def test_authenticationerror_defaults_to_no_context():
    with pytest.raises(AuthenticationError) as e:
        raise AuthenticationError("message")
    assert str(e.value) == "message"
    assert e.value.html_body is None
    assert e.value.status_code is None
    assert e.value.url is None


def test_authenticationerror_carries_diagnostic_context():
    with pytest.raises(AuthenticationError) as e:
        raise AuthenticationError(
            "message", html_body="some body", status_code=403, url="https://example.com"
        )
    assert e.value.html_body == "some body"
    assert e.value.status_code == 403
    assert e.value.url == "https://example.com"


def test_unexpectedloginredirecterror_is_an_authenticationerror():
    """So existing `except AuthenticationError` handling keeps working."""
    err = UnexpectedLoginRedirectError("message", html_body="body", status_code=200)
    assert isinstance(err, AuthenticationError)
    assert err.html_body == "body"
    assert err.status_code == 200
