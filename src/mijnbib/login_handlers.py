from __future__ import annotations

import functools
import logging
import urllib.error
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlsplit

import mechanize
import requests

from mijnbib.const import TIMEOUT, USER_AGENT
from mijnbib.errors import (
    AuthenticationError,
    CanNotConnectError,
    IncompatibleSourceError,
)

_log = logging.getLogger(__name__)


class LoginHandler(ABC):
    def __init__(self, username, password, url: str, br: mechanize.Browser):
        self._username = username
        self._pwd = password
        self._url = url
        self._br = br

    @abstractmethod
    def login(self) -> mechanize.Browser:
        pass


class LoginByForm(LoginHandler):
    def login(self) -> mechanize.Browser:
        response = self._log_in()
        html = response.read().decode("utf-8") if response is not None else ""
        self._validate_logged_in(html)  # raises AuthenticationError if not ok
        return self._br

    def _log_in(self):
        html_string_start_page = "not yet set"  # placeholder for troubleshooting
        try:
            _log.debug("Opening login page ... ")
            response = self._br.open(self._url, timeout=TIMEOUT)
            html_string_start_page = response.read().decode("utf-8")  # type:ignore
            # Workaround for mechanize.BrowserStateError: not viewing HTML
            # because suddenly (March 2024) Content-Type header is "application/octet-stream;charset=UTF-8"
            # which is not recognized as html by mechanize
            # Alternative is to configure the browser instance with
            #     self._br.set_header("Accept", "text/html")
            self._br._factory.is_html = True
            self._br.select_form(nr=0)
            self._br["email"] = self._username
            self._br["password"] = self._pwd
            response = self._br.submit()  # pylint: disable=assignment-from-none
        except mechanize.FormNotFoundError as e:
            raise IncompatibleSourceError(
                "Can not find login form", html_body=html_string_start_page
            ) from e
        except urllib.error.URLError as e:
            # We specifically catch this because site periodically (maintenance?)
            # throws a 500, 502 or 504
            raise CanNotConnectError(
                f"Error while trying to log in at: {self._url}  ({str(e)})", self._url
            ) from e
        return response

    @staticmethod
    def _validate_logged_in(html: str):
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


class LoginByOAuth(LoginHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._s = requests.Session()
        self._s.cookies = self._br.cookiejar  # load cookies from earlier session(s)
        # Set some general request parameters, see https://stackoverflow.com/a/59317604/50899
        self._s.request = functools.partial(self._s.request, timeout=TIMEOUT)  # type: ignore
        self._s.headers["User-Agent"] = USER_AGENT

    def login(self) -> mechanize.Browser:
        response = self._log_in()
        html = response.text if response is not None else ""
        self._validate_logged_in(html)  # raises AuthenticationError if not ok
        self._br.set_cookiejar(self._s.cookies)  # Transfer from requests to mechanize session
        return self._br

    def _log_in(self):
        # Flow is:
        # (1) GET   https://bibliotheek.be/mijn-bibliotheek/aanmelden          ?destination=/mijn-bibliotheek/lidmaatschappen
        #           then, via 302 auto-redirect
        #     GET   https://mijn.bibliotheek.be/openbibid/rest/auth/authorize  ?hint=login&oauth_callback=...&oauth_token=...&uilang=nl
        # (2) POST  https://mijn.bibliotheek.be/openbibid/rest/auth/login
        #           then, via 303 auto-redirect
        #     GET   https://bibliotheek.be/my-library/login/callback           ?oauth_token=...&oauth_verifier=...&uilang=nl
        #           then, via 302 auto-redirect (from destination param)
        #     GET   https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen

        _log.debug("Opening login page ... ")
        response = self._s.get(self._url)
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

        _log.debug("Doing login call ... ")
        data = {
            "hint": qp.get("hint"),  # "login"
            "token": qp.get("oauth_token"),  # 32-char string
            "callback": qp.get("oauth_callback"),  # "https://bibliotheek.be/my-library/login/callback"   # fmt:skip
            "email": self._username,
            "password": self._pwd,
        }
        url = "https://mijn.bibliotheek.be/openbibid/rest/auth/login"
        response = self._s.post(url, data=data)
        return response

    @staticmethod
    def _validate_logged_in(html: str):
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
