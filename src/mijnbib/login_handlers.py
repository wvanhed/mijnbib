from __future__ import annotations

import functools
import logging
import urllib.error
from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlsplit

import mechanize
import requests

from mijnbib.errors import (
    AuthenticationError,
    CanNotConnectError,
    IncompatibleSourceError,
)

_log = logging.getLogger(__name__)


class LoginHandler(ABC):
    @abstractmethod
    def login(self) -> mechanize.Browser:
        pass


class LoginByForm(LoginHandler):
    def __init__(self, username, password, url: str, br: mechanize.Browser):
        self._username = username
        self._pwd = password
        self._url = url
        self._br = br

    def login(self) -> mechanize.Browser:
        response = self._log_in()
        html = response.read().decode("utf-8") if response is not None else ""
        self._validate_logged_in(html)  # raises AuthenticationError if not ok
        return self._br

    def _log_in(self):
        html_string_start_page = "not yet set"  # placeholder for troubleshooting
        try:
            _log.debug("Opening login page ... ")
            response = self._br.open(self._url)  # pylint: disable=assignment-from-none
            html_string_start_page = response.read().decode("utf-8")  # type:ignore
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

    def _validate_logged_in(self, html: str):
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
    def __init__(self, username, password, url: str, br: mechanize.Browser):
        self._username = username
        self._pwd = password
        self._br = br
        self._url = url  # e.g. "https://gent.bibliotheek.be/mijn-bibliotheek/aanmelden"

        self._s = requests.Session()
        # self._s.cookies = self._br.cookiejar # load cookies from earlier session(s)
        # Set some general request parameters, see https://stackoverflow.com/a/59317604/50899
        self._s.request = functools.partial(self._s.request, timeout=30)  # type: ignore
        self._s.headers["User-Agent"] = "Mijnbib"
        self._s.headers["Content-Type"] = "application/json"

    def login(self) -> mechanize.Browser:
        self._log_in()
        self._br.set_cookiejar(self._s.cookies)  # Transfer from requests to mechanize session
        return self._br

    def _log_in(self):
        # Note: flow adapted from https://github.com/myTselection/bibliotheek_be

        # (1) Get OAuth2 state / nonce
        # GET https://gent.bibliotheek.be/mijn-bibliotheek/aanmelden
        # example response:
        # header Location: https://mijn.bibliotheek.be/openbibid/rest/auth/authorize?hint=login&oauth_callback=https://gent.bibliotheek.be/my-library/login/callback&oauth_token=5abee3c0f5c04beead64d8e625ead0e7&uilang=nl
        response = self._s.get(self._url, allow_redirects=False)
        _log.debug(f"login (1) status code       : {response.status_code}")
        _log.debug(f"login (1) headers           : {response.headers}")
        _log.debug(f"login (1) cookies           : {response.cookies}")
        oauth_location_url = response.headers.get("location", "")
        oauth_locationurl_parsed = urlsplit(oauth_location_url)
        query_params = parse_qs(oauth_locationurl_parsed.query)
        oauth_callback_url = query_params.get("oauth_callback")
        oauth_token = query_params.get("oauth_token")
        hint = query_params.get("hint")
        _log.debug(f"login (1) oauth_location_url: {oauth_location_url}")
        _log.debug(f"login (1) oauth_callback_url: {oauth_callback_url}")
        _log.debug(f"login (1) oauth_token       : {oauth_token}")
        _log.debug(f"login (1) hint              : {hint}")
        if response.status_code != 302:
            raise IncompatibleSourceError(
                f"Expected status code 302 during log in. Got '{response.status_code}'",
                response.text,
            )
        if "/mijn-bibliotheek/overzicht" in oauth_location_url:
            _log.info("Already authenticated. No need to log in again.")
            return

        # (2) Authorize based on Location url (get session id)
        response = self._s.get(oauth_location_url, allow_redirects=False)
        _log.debug(f"login (2) status code       : {response.status_code}")
        _log.debug(f"login (2) headers           : {response.headers}")
        _log.debug(f"login (2) cookies           : {response.cookies}")
        if response.status_code != 200:
            raise IncompatibleSourceError(
                f"Expected status code 200 during log in. Got '{response.status_code}'",
                response.text,
            )

        # (3) Login with username, password & token
        # example response:
        # header Location: https://gent.bibliotheek.be/my-library/login/callback?oauth_token=*********&oauth_verifier=*********&uilang=nl
        url = "https://mijn.bibliotheek.be/openbibid/rest/auth/login"
        data = {
            "hint": hint,
            "token": oauth_token,
            "callback": oauth_callback_url,
            "email": self._username,
            "password": self._pwd,
        }
        response = self._s.post(url, data=data, allow_redirects=False)
        _log.debug(f"login (3) status code       : {response.status_code}")
        _log.debug(f"login (3) headers           : {response.headers}")
        login_location_url = response.headers.get("location", "")
        login_locationurl_parsed = urlsplit(login_location_url)
        login_query_params = parse_qs(login_locationurl_parsed.query)
        oauth_verifier = login_query_params.get("oauth_verifier")
        oauth_token = query_params.get("oauth_token")
        hint = query_params.get("hint")
        _log.debug(f"login (3) login_location_url: {login_location_url}")
        _log.debug(f"login (3) oauth_verifier    : {oauth_verifier}")
        _log.debug(f"login (3) oauth_token       : {oauth_token}")
        _log.debug(f"login (3) hint              : {hint}")
        if response.status_code == 200:
            raise AuthenticationError("Login not accepted. Correct credentials?")
        if response.status_code != 303:
            raise IncompatibleSourceError(
                f"Expected status code 303 during log in. Got '{response.status_code}'",
                response.text,
            )

        # (4) Call login callback based on Location url
        response = self._s.get(login_location_url, allow_redirects=False)
        _log.debug(f"login (4) status code       : {response.status_code}")
        _log.debug(f"login (4) headers           : {response.headers}")
        _log.debug(f"login (4) cookies           : {response.cookies}")
        # _log.debug(f"login (4) text              : {response.text}")

        # Soft verification if we are logged in
        if ("mijn-bibliotheek/overzicht" not in response.headers.get("location", "")) and (
            "mijn-bibliotheek/lidmaatschappen" not in response.headers.get("location", "")
        ):
            _log.warning(
                "Not clear if properly logged in. Was expecting "
                "'mijn-bibliotheek/overzicht' or 'mijn-bibliotheek/lidmaatschappen' "
                "in location header, but couldn't find it"
            )
