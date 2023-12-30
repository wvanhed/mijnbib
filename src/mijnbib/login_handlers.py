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
        response = self._log_in(self._url)  # TODO: remove parameter
        html = response.read().decode("utf-8") if response is not None else ""
        self._validate_logged_in(html)  # raises AuthenticationError if not ok
        return self._br

    def _log_in(self, url):
        html_string_start_page = "not yet set"  # placeholder for troubleshooting
        try:
            _log.debug("Opening login page ... ")
            response = self._br.open(url)  # pylint: disable=assignment-from-none
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
                f"Error while trying to log in at: {url}  ({str(e)})", url
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


# TODO clean up assert statements
# TODO: check invalid credentials case
# TODO: check already logged in behaviour
class LoginByOAuth(LoginHandler):
    def __init__(self, username, password, url: str, br: mechanize.Browser):
        self._username = username
        self._pwd = password
        self._br = br

        # e.g. "https://gent.bibliotheek.be/mijn-bibliotheek/aanmelden"
        self._url = url
        url_splitter = urlsplit(url)
        # e.g. "https://gent.bibliotheek.be"
        self._base_url = f"{url_splitter.scheme}://{url_splitter.netloc}"

        self._s = requests.Session()
        # Set some general request parameters, see https://stackoverflow.com/a/59317604/50899
        self._s.request = functools.partial(self._s.request, timeout=30)  # type: ignore
        self._s.headers["User-Agent"] = "Mijnbib"
        self._s.headers["Content-Type"] = "application/json"

    def login(self) -> mechanize.Browser:
        response = self._log_in()
        html = response.text if response is not None else ""
        self._validate_logged_in(html)

        # Transfer cookies from requests session to mechanize browser
        self._br.set_cookiejar(self._s.cookies)
        # for cookie in self._br._ua_handlers["_cookies"].cookiejar:
        #     print(cookie)

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
            # Return if already authenticated
            return True  # TODO: fix

        # (2) Authorize based on Location url (get session id)
        response = self._s.get(oauth_location_url, allow_redirects=False)
        _log.debug(f"login (2) status code       : {response.status_code}")
        _log.debug(f"login (2) headers           : {response.headers}")
        _log.debug(f"login (2) cookies           : {response.cookies}")
        assert response.status_code == 200

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
        _log.debug(f"login (3) cookies           : {response.cookies}")  # no cookies
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
        assert response.status_code == 303

        # (4) Call login callback based on Location url
        response = self._s.get(login_location_url, allow_redirects=False)
        _log.debug(f"login (4) status code       : {response.status_code}")
        _log.debug(f"login (4) headers           : {response.headers}")
        _log.debug(f"login (4) cookies           : {response.cookies}")
        # _log.debug(f"login (4) text              : {response.text}")

        # NOTE: Old code from https://github.com/myTselection/bibliotheek_be, to check/clean-up
        # assert response.status_code == 302
        # if response.status_code == 302:
        #     # request access code, https://mijn.bibliotheek.be/openbibid-api.html#_authenticatie
        #     data = {"hint": hint, "token": oauth_token, "callback":"https://bibliotheek.be/my-library/login/callback", "email": username, "password": password}
        #     response = self.s.post('https://mijn.bibliotheek.be/openbibid/rest/accessToken',headers=header,data=data,timeout=_TIMEOUT,allow_redirects=False)
        #     _LOGGER.debug(f"bibliotheek.be login get result status code: {response.status_code}")
        # else:
        #     #login session was already available
        #     login_callback_location = "https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen"

        # (5) Open a useful page to confirm we're properly logged in.
        # The Location header (from above) refers to "mijn-bibliotheek/overzicht", but this page is slow to open.
        # So don't go there, but go to lidmaatschappen instead.
        url = self._base_url + "/mijn-bibliotheek/lidmaatschappen"
        response = self._s.get(f"{url}", allow_redirects=False)
        assert response.status_code == 200
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
        if "Aangemeld als" not in html:
            raise AuthenticationError("Login not accepted (2)")
        _log.debug("Login was successful")
