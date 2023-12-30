from __future__ import annotations

import logging
import urllib.error

import mechanize

from mijnbib.errors import (
    AuthenticationError,
    CanNotConnectError,
    IncompatibleSourceError,
)

_log = logging.getLogger(__name__)


class LoginByForm:
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
