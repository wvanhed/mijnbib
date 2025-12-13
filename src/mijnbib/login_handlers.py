from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlsplit

import requests

from mijnbib.errors import AuthenticationError

_log = logging.getLogger(__name__)


class LoginByOAuth:
    def __init__(self, username, password, url: str, ses: requests.Session):
        self._username = username
        self._pwd = password
        self._url = url
        self._ses = ses

    def login(self) -> requests.Session:
        response = self._log_in()
        html = response.text if response is not None else ""
        _validate_logged_in(html)  # raises AuthenticationError if not ok
        return self._ses

    def _log_in(self) -> requests.Response:
        # Flow is:
        # (1) GET   https://bibliotheek.be/mijn-bibliotheek/aanmelden          ?destination=/mijn-bibliotheek/lidmaatschappen
        #           then, via 302 auto-redirect
        #     GET   https://mijn.bibliotheek.be/openbibid/rest/auth/authorize  ?hint=login&oauth_callback=...&oauth_token=...&uilang=nl
        # (2) POST  https://mijn.bibliotheek.be/openbibid/rest/auth/login
        #           then, via 303 auto-redirect
        #     GET   https://bibliotheek.be/my-library/login/callback           ?oauth_token=...&oauth_verifier=...&uilang=nl
        #           then, via 302 auto-redirect (from destination param)
        #     GET   https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen

        _log.debug("(1) Opening login page ... ")
        response = self._ses.get(self._url)
        # Will perform auto-redirect to
        # https://mijn.bibliotheek.be/openbibid/rest/auth/authorize?
        #   hint=login&oauth_callback=https%3A//bibliotheek.be/my-library/login/callback
        #   &oauth_token=*******&uilang=nl
        auth_url = response.url
        auth_url_parsed = urlsplit(auth_url)
        qp = parse_qs(auth_url_parsed.query)
        _log.debug(f"auth_url     : {auth_url}")
        _log.debug(f"query params : {qp}")
        if qp == {}:
            _log.debug("Looks like we are still or already logged in. Skip auth/login call")
            return response

        _log.debug("(2) Doing login call ... ")
        data = {
            "hint": qp.get("hint"),  # "login"
            "token": qp.get("oauth_token"),  # 32-char string
            "callback": qp.get("oauth_callback"),  # "https://bibliotheek.be/my-library/login/callback"
            "email": self._username,
            "password": self._pwd,
        }  # fmt:skip
        url = "https://mijn.bibliotheek.be/openbibid/rest/auth/login"
        response = self._ses.post(url, data=data)
        return response


def _validate_logged_in(html: str) -> None:
    """Raise AuthenticationError if login failed."""
    _log.debug("Checking if login is successful ...")
    if "Profiel" not in html:
        if (
            "privacyverklaring is gewijzigd" in html
            or "akkoord met de privacyverklaring" in html
        ):
            raise AuthenticationError(
                "Login not accepted (likely need to accept privacy statement again)"
            )
        else:
            raise AuthenticationError("Login not accepted")
    _log.debug("Login was successful")
