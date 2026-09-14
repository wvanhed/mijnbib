from __future__ import annotations

import pytest
import requests

from mijnbib.errors import AuthenticationError, UnexpectedLoginRedirectError
from mijnbib.login_handlers import LoginByOAuth

LOGIN_URL = "https://bibliotheek.be/mijn-bibliotheek/aanmelden?destination=/mijn-bibliotheek/lidmaatschappen"
AUTHORIZE_URL = (
    "https://mijn.bibliotheek.be/openbibid/rest/auth/authorize"
    "?hint=login&oauth_callback=https://bibliotheek.be/my-library/login/callback"
    "&oauth_token=abc123&uilang=nl"
)
LOGIN_POST_URL = "https://mijn.bibliotheek.be/openbibid/rest/auth/login"


def test_login_raises_unexpectedloginredirecterror_when_oauth_redirect_missing(requests_mock):
    """If the login page doesn't redirect into the oauth flow (no oauth_token in the
    resulting URL), that means the request never reached real credential checking -
    e.g. because it was intercepted/blocked. We should get a clearly-named error
    instead of silently POSTing a login request with token=None/callback=None.
    """
    requests_mock.get(LOGIN_URL, status_code=200, text="some page, no redirect happened")

    handler = LoginByOAuth("user", "pwd", LOGIN_URL, requests.Session())

    with pytest.raises(UnexpectedLoginRedirectError, match=r".*no oauth_token.*") as e:
        handler.login()

    assert e.value.status_code == 200
    assert e.value.url == LOGIN_URL
    assert e.value.html_body == "some page, no redirect happened"


def test_login_raises_authenticationerror_when_oauth_flow_completes_but_rejected(
    requests_mock,
):
    """If the oauth redirect *does* happen (real credential check is reached) but the
    final page isn't a logged-in profile page, that's a genuine login rejection
    (e.g. wrong credentials) - a plain AuthenticationError, not the redirect-missing one.
    """
    requests_mock.get(
        LOGIN_URL,
        status_code=302,
        headers={"location": AUTHORIZE_URL},
    )
    requests_mock.get(AUTHORIZE_URL, status_code=200, text="irrelevant authorize page body")
    requests_mock.post(LOGIN_POST_URL, status_code=200, text="rejected, back to login form")

    handler = LoginByOAuth("user", "wrongpwd", LOGIN_URL, requests.Session())

    with pytest.raises(AuthenticationError, match=r".*Login not accepted.*") as e:
        handler.login()

    assert not isinstance(e.value, UnexpectedLoginRedirectError)
    assert e.value.status_code == 200
    assert e.value.url == LOGIN_POST_URL
    assert e.value.html_body == "rejected, back to login form"


def test_login_succeeds_when_oauth_flow_completes_and_profile_found(requests_mock):
    requests_mock.get(
        LOGIN_URL,
        status_code=302,
        headers={"location": AUTHORIZE_URL},
    )
    requests_mock.get(AUTHORIZE_URL, status_code=200, text="irrelevant authorize page body")
    requests_mock.post(LOGIN_POST_URL, status_code=200, text="Welcome, see your Profiel here")

    handler = LoginByOAuth("user", "pwd", LOGIN_URL, requests.Session())

    handler.login()  # should not raise
