"""Webscraper module for interacting with the mijn.bibliotheek.be website.

Created (initial version) on July 14, 2015

For usage of this module, see the examples folder and the docstrings
in the MijnBibliotheek class and its public methods.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

import mechanize

from mijnbib.const import TIMEOUT, USER_AGENT
from mijnbib.errors import (
    ExtendLoanError,
    IncompatibleSourceError,
    InvalidExtendLoanURL,
    ItemAccessError,
    TemporarySiteError,
)
from mijnbib.login_handlers import LoginByForm, LoginByOAuth
from mijnbib.models import Account, Loan, Reservation
from mijnbib.parsers import (
    AccountsListPageParser,
    ExtendResponsePageParser,
    LoansListPageParser,
    ReservationsPageParser,
)

_log = logging.getLogger(__name__)


class MijnBibliotheek:
    BASE_DOMAIN = "bibliotheek.be"

    def __init__(self, username: str, password: str, city: str | None = None, login_by="form"):
        """API for interacting with the mijn.bibliotheek.be website.

        Args:
            username:   username or email address
            password:   password
            city    :   Optional. Subdomain for the bibliotheek.be website,
                        typically your city.
            login_by:   Optional. Either `form` (default) or `oauth`. Specfies
                        whether authentication happens via a web-based login
                        form (slow), or via OAauth (2x faster, but more complex flow)
        """
        _log.debug(f"Initializing {USER_AGENT}. (login_by: '{login_by}')")
        self._username = username
        self._pwd = password

        subdomain = ""
        if city is not None and city != "":
            subdomain = city.lower().strip() + "."
        self.BASE_URL = f"https://{subdomain}{self.BASE_DOMAIN}"

        if login_by == "oauth":
            self._login_handler_class = LoginByOAuth
        elif login_by == "form":
            self._login_handler_class = LoginByForm
        else:
            raise ValueError("login_by needs to be either 'oauth' or 'form'")

        self._logged_in = False

        self._br = mechanize.Browser()
        self._br.set_handle_robots(False)
        self._br.set_header("User-Agent", USER_AGENT)

        # Open the door for overriding parsers (but still keep private for now)
        self._loans_page_parser = LoansListPageParser()
        self._accounts_page_parser = AccountsListPageParser()
        self._reservations_parser = ReservationsPageParser()
        self._extend_response_page_parser = ExtendResponsePageParser()

    # *** PUBLIC METHODS ***

    def login(self) -> None:
        """Log in. Is auto-called by other methods if needed.

        Raises:
            AuthenticationError
            CanNotConnectError
            IncompatibleSourceError
            TemporarySiteError
        """
        url = (
            self.BASE_URL
            + "/mijn-bibliotheek/aanmelden"
            # loads considerably faster than default "/overzicht" page, especially for cold cache
            + "?destination=/mijn-bibliotheek/lidmaatschappen"
        )
        _log.info(f"Will log in at url : {url}")
        _log.info(f"           with id : {self._username}")

        login_handler = self._login_handler_class(self._username, self._pwd, url, self._br)
        self._br = login_handler.login()  # May raise AuthenticationError

        self._logged_in = True

    def get_loans(self, account_id: str) -> list[Loan]:
        """Return list of loans. Will login first if needed.

        Raises:
            AuthenticationError
            IncompatibleSourceError
            ItemAccessError: something went wrong fetching loans
            TemporarySiteError
        """
        _log.info(f"Retrieving loans for account: '{account_id}'")
        if not self._logged_in:
            self.login()

        url = self.BASE_URL + f"/mijn-bibliotheek/lidmaatschappen/{account_id}/uitleningen"
        html_string = self._open_account_loans_page(url)
        try:
            loans = self._loans_page_parser.parse(html_string, self.BASE_URL, account_id)
        except TemporarySiteError as e:
            raise e
        except Exception as e:
            raise IncompatibleSourceError(
                f"Problem scraping loans ({str(e)})", html_body=""
            ) from e
        return loans

    def get_reservations(self, account_id: str) -> list[Reservation]:
        """Return list of reservations. Will login first if needed.

        Raises:
            AuthenticationError
            IncompatibleSourceError
            ItemAccessError: something went wrong fetching reservations
        """
        _log.info(f"Retrieving reservations for account: '{account_id}'")
        if not self._logged_in:
            self.login()

        url = self.BASE_URL + f"/mijn-bibliotheek/lidmaatschappen/{account_id}/reservaties"
        html_string = self._open_account_loans_page(url)  #  same structure as for loans
        try:
            holds = self._reservations_parser.parse(html_string)
        except Exception as e:
            raise IncompatibleSourceError(
                f"Problem scraping reservations ({str(e)})", html_body=""
            ) from e
        return holds

    def get_accounts(self) -> list[Account]:
        """Return list of accounts. Will login first if needed.

        Raises:
            AuthenticationError
            IncompatibleSourceError
        """
        _log.info("Retrieving accounts")
        if not self._logged_in:
            self.login()

        url = self.BASE_URL + "/mijn-bibliotheek/lidmaatschappen"
        _log.debug(f"Opening page '{url}' ... ")
        response = self._br.open(url, timeout=TIMEOUT)  # pylint: disable=assignment-from-none
        html_string = response.read().decode("utf-8")  # type:ignore
        try:
            accounts = self._accounts_page_parser.parse(html_string, self.BASE_URL)
        except Exception as e:
            raise IncompatibleSourceError(
                f"Problem scraping accounts ({str(e)})", html_body=""
            ) from e
        return accounts

    def get_all_info(self, all_as_dicts=False) -> dict:
        """Return all available information, for all accounts.

        Information is returned as a dict, with account ids as keys.

        Args:
            all_as_dicts:   When True, do not return dataclass objects, but dicts
                            instead.
        Raises:
            AuthenticationError
            IncompatibleSourceError
            ItemAccessError: something went wrong fetching loans or reservations
        """
        _log.info("Retrieving all information")
        info = {}
        accounts = self.get_accounts()
        for a in accounts:
            loans = self.get_loans(a.id) if a.loans_count != 0 else []
            holds = self.get_reservations(a.id) if a.reservations_count != 0 else []
            info[a.id] = {
                "account_details": a if not all_as_dicts else asdict(a),
                "loans": loans if not all_as_dicts else [asdict(loan) for loan in loans],
                "reservations": (
                    holds if not all_as_dicts else [asdict(hold) for hold in holds]
                ),
            }
        return info

    def extend_loans(self, extend_url: str, execute: bool = False) -> tuple[bool, dict]:
        """Extend given loan(s) via extend_url. Will login first if needed.

        The url looks like
        https://city.bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123/uitleningen/verlengen?loan-ids=456%2C789
        Multiple ids can be given for the loan-ids query parameter, separated by
        a comma (which is url-encoded as '%2C'). In the example above the IDs 456
        and 789 will be extended.

        Evaluating if a loan extension was successful, is currently a bit of black
        wizardry. You should consider both the `success` response value (True/False)
        as well as the absence or occurrence of an error as /suggesting/ success.
        This is partially due to the ambiguity of the server response; however
        there is also room for handling it more consistently (e.g. returning
        `success==False`, rather then raising an ExtendLoanError)

        Args:
            extend_url: url to use for extending one or multiple loans
            execute: A development flag; set to True actually perform loan extension
        Returns:
            A result tuple (success, details).
            The `success` element is True if extension was successful, False otherwise.
            The `details` element contains a dictionary with more details; consider
            it for debugging purposes.
        Raises:
            AuthenticationError
            IncompatibleSourceError
            InvalidExtendLoanURL
            ExtendLoanError
        """
        # NOTE: would make more sense to return loan list (since final page is loan page)
        # Perhaps retrieving those loans again, and check extendability would also be good idea.
        if not self._logged_in:
            self.login()

        _log.info(f"Will extend loan via url: {extend_url}")
        try:
            response = self._br.open(extend_url, timeout=TIMEOUT)
        except mechanize.HTTPError as e:
            if e.code == 500:
                raise InvalidExtendLoanURL(
                    f"Probably invalid extend loan URL: {extend_url}"
                ) from e
            else:
                raise e

        try:
            self._br.select_form(id="my-library-extend-loan-form")
        except mechanize.FormNotFoundError as e:
            raise IncompatibleSourceError("Can not find extend loan form", html_body="") from e

        if not execute:
            _log.warning("SIMULATING extending the loan. Will stop now.")
            return False, {}

        try:
            response = self._br.submit()  # pylint: disable=assignment-from-none
        except mechanize.HTTPError as e:
            if e.code == 500:
                # duh, server crashes on unexpected id or id combinations
                # (e.g. nonexisting id, ids that belong to different library accounts)
                # However, if multiple id's, some of them *might* have been extended,
                # even if 500 response
                raise ExtendLoanError(f"Could not extend loans using url: {extend_url}") from e
            else:
                raise e

        # disclaimer: not sure if other codes are realistic
        success = response.code == 200 if response is not None else False

        if success:
            _log.debug("Looks like extending the loan(s) was successful")

        # Try to add result details, but don't fail if we fail to parse details, it's tricky :-)
        try:
            # On submit, we arrive at "uitleningen" (loans) page, which lists the result
            html_string = response.read().decode("utf-8")  # type:ignore
            # Path("response.html").write_text("html_string")  # for debugging
            details = self._extend_response_page_parser.parse(html_string)
            if "likely_success" in details and details["likely_success"] is False:
                # Probably valid page (http=200) but with 'Foutmelding'
                success = False
        except Exception as e:
            _log.warning(f"Could not parse loan extending result. Error: {e}")
            details = {}

        return success, details

    def extend_loans_by_ids(
        self, acc_extids: list[tuple[str, str]], execute: bool = False
    ) -> tuple[bool, dict]:
        """Extend loan(s) via list of (account_id, extend_id) tuples. Will login first if needed.

        For return value, exceptions thrown and more details, see `extend_loans()`

        Args:
            acc_extids: List of (account_id, extend_id) tuples
            execute:  A development flag; set to True actually perform loan extension
        """
        _log.info(f"Extending loans via ids: '{acc_extids}'")
        if not acc_extids:
            raise ValueError("List must not be empty.")
        account_id, _extend_id = acc_extids[0]  # use first acc id for general account id
        ids = [f"{acc_id}|{ext_id}" for (acc_id, ext_id) in acc_extids]
        ids = ",".join(ids)
        url = (
            self.BASE_URL
            + f"/mijn-bibliotheek/lidmaatschappen/{account_id}/uitleningen/verlengen"
            + f"?loan-ids={ids}"
        )
        return self.extend_loans(url, execute)

    # *** INTERNAL METHODS ***

    def _open_account_loans_page(self, acc_url: str) -> str:
        _log.debug(f"Opening page '{acc_url}' ... ")
        try:
            response = self._br.open(acc_url, timeout=TIMEOUT)
        except mechanize.HTTPError as e:
            if e.code == 404:
                raise ItemAccessError(
                    "Loans url can not be opened (404 reponse). Likely incorrect or "
                    f"nonexisting account ID in the url '{acc_url}'"
                ) from e
            if e.code == 500:
                raise TemporarySiteError(
                    f"Loans url can not be opened (500 response), url '{acc_url}'"
                ) from e
            raise ItemAccessError(
                f"Loans url can not be opened. Reason unknown. Error: {e}"
            ) from e

        html = response.read().decode("utf-8") if response is not None else ""
        return html
