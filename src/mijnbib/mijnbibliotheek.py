"""Webscraper module for interacting with the mijn.bibliotheek.be website.

Created (initial version) on July 14, 2015

For usage of this module, see the examples folder and the docstrings
in the MijnBibliotheek class and its public methods.
"""

from __future__ import annotations

import functools
import json
import logging
import warnings
from dataclasses import asdict

import requests

from mijnbib.const import TIMEOUT, USER_AGENT
from mijnbib.errors import (
    ExtendLoanError,
    IncompatibleSourceError,
    ItemAccessError,
    TemporarySiteError,
)
from mijnbib.login_handlers import LoginByOAuth
from mijnbib.models import Account, Loan, Reservation
from mijnbib.parsers import (
    ExtendResponsePageParser,
    LoansListPageParser,
    ReservationsPageParser,
)

_log = logging.getLogger(__name__)


class MijnBibliotheek:
    BASE_DOMAIN = "bibliotheek.be"

    def __init__(
        self, username: str, password: str, city: str | None = None, login_by="oauth"
    ):
        """API for interacting with the mijn.bibliotheek.be website.

        Args:
            username:   username or email address
            password:   password
            city    :   Optional. Subdomain for the bibliotheek.be website,
                        typically your city.
            login_by:   Optional. Legacy option `form` has been removed,
                        and is auto-replaced by `oauth`.
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
            warnings.warn(
                "'form' login_by option is deprecated and is auto-replaced by 'oauth'.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._login_handler_class = LoginByOAuth
        else:
            raise ValueError("login_by needs to be either 'oauth' or 'form' (deprecated)")

        self._logged_in = False

        self._ses = requests.Session()
        # Set some general request parameters, see https://stackoverflow.com/a/59317604/50899
        self._ses.request = functools.partial(self._ses.request, timeout=TIMEOUT)  # type: ignore
        self._ses.headers.update({"User-Agent": USER_AGENT})

        # Open the door for overriding parsers (but still keep private for now)
        self._loans_page_parser = LoansListPageParser()
        self._reservations_parser = ReservationsPageParser()
        self._extend_response_page_parser = ExtendResponsePageParser()

    # *** PUBLIC METHODS ***

    def login(self) -> None:
        """Log in. Is auto-called by other methods if needed.

        Raises:
            AuthenticationError
        """
        url = (
            self.BASE_URL
            + "/mijn-bibliotheek/aanmelden"
            # loads considerably faster than default "/overzicht" page, especially for cold cache
            + "?destination=/mijn-bibliotheek/lidmaatschappen"
        )
        _log.info(f"Will log in at url : {url}")
        _log.info(f"           with id : {self._username}")

        login_handler = self._login_handler_class(self._username, self._pwd, url, self._ses)
        self._ses = login_handler.login()  # May raise AuthenticationError

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
                f"Problem scraping loans ({e!s})", html_body=html_string
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
                f"Problem scraping reservations ({e!s})", html_body=html_string
            ) from e
        return holds

    def get_accounts(self) -> list[Account]:
        """Return list of accounts. Will login first if needed.

        Each account also contains some data about current number of loans,
        reservations and open amount.

        Raises:
            AuthenticationError
            IncompatibleSourceError
        """
        _log.info("Retrieving accounts")
        if not self._logged_in:
            self.login()

        # Fetch the accounts (= memberships) from the API
        memberships_api_url = f"{self.BASE_URL}/api/my-library/memberships"
        _log.debug(f"Fetching memberships data (json) from '{memberships_api_url}' ... ")
        response = self._ses.get(memberships_api_url)
        try:
            memberships_data = json.loads(response.text)
            memberships = _parse_api_memberships(memberships_data)
        except Exception as e:
            raise IncompatibleSourceError(
                f"Failed to fetch memberhips/accounts: '{type(e).__name__}: {e!s}'",
                html_body=response.text,
            ) from e

        _log.debug("Number of accounts found: %s", len(memberships))

        # Fetch activities for each account, and create Account objects
        accounts = []
        for ms in memberships:
            if "hasError" not in ms:
                raise IncompatibleSourceError(
                    "Unexpected JSON structure for memberships/accounts. Was expecting key 'hasError'.",
                    html_body=str(memberships),
                )
            if ms["hasError"] is True:
                # Note: this is an assumption, have not yet observed this in practice
                _log.warning(f"Account {ms['id']} reports error, skipping counts and amounts")
                loans_count = None
                reservations_count = None
                open_amounts = 0
            else:
                # Fetch activities for this account, to get counts and amounts
                try:
                    activities_api_url = (
                        f"{self.BASE_URL}/api/my-library/{ms['id']}/activities"
                    )
                    _log.debug(
                        f"Fetching activity data (json) from '{activities_api_url}' ... "
                    )
                    response = self._ses.get(activities_api_url)
                    response.raise_for_status()
                    activity_data = json.loads(response.text)

                    loans_count = activity_data.get("numberOfLoans", 0)
                    reservations_count = activity_data.get("numberOfHolds", 0)
                    open_amounts = float(
                        activity_data.get("openAmount", "0,00").replace(",", ".")
                    )
                except requests.RequestException as e:
                    raise e
                except Exception as e:
                    raise IncompatibleSourceError(
                        f"Failed to fetch activity data for account {ms['id']}: '{type(e).__name__}: {e!s}'",
                        html_body=response.text,
                    ) from e

            acc = Account(
                id=ms["id"],
                library_name=ms["libraryName"],
                user=ms["name"],
                loans_url=f"{self.BASE_URL}/mijn-bibliotheek/lidmaatschappen/{ms['id']}/uitleningen",
                reservations_url=f"{self.BASE_URL}/mijn-bibliotheek/lidmaatschappen/{ms['id']}/reservaties",
                open_amounts_url=f"{self.BASE_URL}/mijn-bibliotheek/lidmaatschappen/{ms['id']}/te-betalen",
                loans_count=loans_count,
                reservations_count=reservations_count,
                open_amounts=open_amounts,
            )
            accounts.append(acc)

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

    def extend_loans(
        self, extend_url: str, execute: bool = False
    ) -> tuple[bool, list[Loan] | None, dict]:
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
            A result tuple (success, loans, details).
            - `success`: True if extension was successful, False otherwise.
            - `loans`:   list of all Loan objects, after extension attempt. None if parsing failed.
            - `details`: a dictionary with more details, might be empty; consider it for
                         debugging purposes.
        Raises:
            AuthenticationError
            IncompatibleSourceError
            ExtendLoanError
        """
        if not self._logged_in:
            self.login()

        _log.info(f"Will extend loan via url: {extend_url}")

        # Referer header is needed (otherwise 500 error), and determines page redirected to
        account_id = extend_url.split("/")[5]  # Add more robust parsing?
        referer_url = (
            self.BASE_URL + f"/mijn-bibliotheek/lidmaatschappen/{account_id}/uitleningen"
        )
        self._ses.headers.update({"Referer": referer_url})
        _log.debug(f"Will add the following headers: {self._ses.headers}")

        if not execute:
            _log.warning("SIMULATING extending the loan. Will stop now.")
            return False, [], {}

        # Extend loan(s)
        try:
            response = self._ses.get(extend_url)
            response.raise_for_status()
        except requests.HTTPError as e:
            if e.response.status_code == 500:
                # duh, server crashes on unexpected id or id combinations
                # (e.g. nonexisting id, ids that belong to different library accounts)
                # However, if multiple id's, some of them *might* have been extended,
                # even if 500 response
                raise ExtendLoanError(f"Could not extend loans using url: {extend_url}") from e
            else:
                raise e
        finally:
            self._ses.headers.pop("Referer")  # clean up

        # disclaimer: not sure if other codes are realistic
        success = response.status_code == 200

        if success:
            _log.debug("Looks like extending the loan(s) was successful")

        # Try to add result details, but don't fail if we fail to parse details, it's tricky :-)
        try:
            # We get redirected to "uitleningen" (loans) page, which lists
            # (a) extension results and (b) all loans
            html_string = response.text
            # Path("response.html").write_text(html_string)  # for debugging
            details = self._extend_response_page_parser.parse(html_string)
            if "likely_success" in details and details["likely_success"] is False:
                # Probably valid page (http=200) but with 'Foutmelding'
                success = False
            # Parse all loans (includes extended ones)
            loans = self._loans_page_parser.parse(html_string, self.BASE_URL, account_id)
        except Exception as e:
            _log.warning(f"Could not parse loan extending result. Error: {e}")
            loans = None
            details = {}
        _log.debug(f"Extend loan details: {details}")

        return success, loans, details

    def extend_loans_by_ids(
        self, acc_extids: list[tuple[str, str]], execute: bool = False
    ) -> tuple[bool, list[Loan] | None, dict]:
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
            response = self._ses.get(acc_url)
            if response.status_code == 404:
                raise ItemAccessError(
                    "Loans url can not be opened (404 reponse). Likely incorrect or "
                    f"nonexisting account ID in the url '{acc_url}'"
                )
            if response.status_code == 500:
                raise TemporarySiteError(
                    f"Loans url can not be opened (500 response), url '{acc_url}'"
                )
        except requests.RequestException as e:
            raise ItemAccessError(
                f"Loans url can not be opened. Reason unknown. Error: {e}"
            ) from e

        html = response.text
        return html


def _parse_api_memberships(memberships_data: dict) -> list[dict]:
    membership_list = []
    for _region_name, provider in memberships_data.items():
        region = provider["region"]
        for _rijksregisternr, memberships in region.items():
            membership_list.extend(memberships)
    return membership_list
