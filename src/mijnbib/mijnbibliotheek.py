"""
Webscraper module, for interacting with the mijn.bibliotheek.be website.
Created (initial version) on July 14, 2015

For example usage of this module, see the main method at the bottom of the file 
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import date, datetime

import mechanize
from bs4 import BeautifulSoup

from mijnbib.plugin_errors import (
    AccessError,
    AuthenticationError,
    CanNotConnectError,
    ExtendLoanError,
    IncompatibleSourceError,
)

_log = logging.getLogger(__name__)

# CHEAT SHEET - BeautifulSoup (aka, things I always forget)
#
# .get_text()   It returns all the text in a document or beneath a tag, as a
#               single Unicode string. Probably preferred over .string
# .text         Seems to be shorthand for .get_text().
# .string       Typically returns the single string withing a tag, but can also
#               return None, or the string from the single-containing tag. It's
#               complicated, see also https://stackoverflow.com/a/25328374/50899


class MijnBibliotheek:
    """API for interacting with the mijn.bibliotheek.be website."""

    BASE_DOMAIN = "bibliotheek.be"
    DATE_FORMAT = "%d/%m/%Y"

    def __init__(self, username: str, password: str, city: str) -> None:
        self._username = username
        self._pwd = password

        self.BASE_URL = f"https://{city.lower().strip()}.{self.BASE_DOMAIN}"
        self._logged_in = False

        self._br = mechanize.Browser()
        self._br.set_handle_robots(False)

    # *** PUBLIC METHODS ***

    def login(self) -> None:
        """Log in. Is auto-called by other methods if needed.

        Raises:
            CanNotConnectError
            AuthenticationError
            IncompatibleSourceError
        """
        url = self.BASE_URL + "/mijn-bibliotheek/aanmelden"
        _log.debug(f"Will log in at url : {url}")
        _log.debug(f"           with id : {self._username}")

        response = self._log_in(url)
        self._validate_logged_in(response)  # raises AuthenticationError if not ok

        self._logged_in = True

    def get_loans(self, account_id: str) -> list[Loan]:
        """Return list of loans. Will login first if needed.

        Raises:
            AccessError: something went wrong fetching loans
            AuthenticationError
            IncompatibleSourceError
        """
        if not self._logged_in:
            self.login()

        url = self.BASE_URL + f"/mijn-bibliotheek/lidmaatschappen/{account_id}/uitleningen"
        html_string = self._open_account_loans_page(url)
        try:
            loans = self._parse_account_loan_page(html_string, self.BASE_URL)
        except Exception as e:
            raise IncompatibleSourceError(f"Problem scraping loans ({str(e)})", "") from e
        return loans

    def get_reservations(self, account_id: str) -> list[Reservation]:
        """Return list of reservations. Will login first if needed.

        Raises:
            AccessError: something went wrong fetching reservations
            AuthenticationError
            IncompatibleSourceError
        """
        if not self._logged_in:
            self.login()

        url = self.BASE_URL + f"/mijn-bibliotheek/lidmaatschappen/{account_id}/reservaties"
        html_string = self._open_account_loans_page(url)  #  same structure as for loans
        try:
            holds = self._parse_account_reservations_page(html_string)
        except Exception as e:
            raise IncompatibleSourceError(
                f"Problem scraping reservations ({str(e)})", ""
            ) from e
        return holds

    def get_accounts(self) -> list[Account]:
        """Return list of accounts. Will login first if needed.

        Raises:
            IncompatibleSourceError
        """
        if not self._logged_in:
            self.login()

        url = self.BASE_URL + "/mijn-bibliotheek/lidmaatschappen"
        _log.debug("Opening page 'lidmaatschappen' ... ")
        response = self._br.open(url)  # pylint: disable=assignment-from-none
        html_string = response.read().decode("utf-8")  # type:ignore
        try:
            accounts = self._parse_accounts_list_page(html_string, self.BASE_URL)
        except Exception as e:
            raise IncompatibleSourceError(f"Problem scraping accounts ({str(e)})", "") from e
        return accounts

    def get_all_info(self, all_as_dicts=False) -> dict:
        """Returns all available information, for all accounts.

        Information is returned as a dict, with account ids as keys.

        Args:
            all_as_dicts    When True, do not return dataclass objects, but dicts
                            instead.
        Raises:
            AccessError: something went wrong fetching loans or reservations
            AuthenticationError
            IncompatibleSourceError
        """
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
            execute: A development flag; set to True actually perform loan extension
        Returns:
            A result tuple (success, details).
            The `success` element is True if extension was successful, False otherwise.
            The `details` element contains a dictionary with more details; consider
            it for debugging purposes.
        Raises:
            ExtendLoanError: raised when a loan could not be extended
            IncompatibleSourceError
        """
        # TODO: would make more sense to return loan list (since final page is loan page)
        if not self._logged_in:
            self.login()

        _log.debug(f"Will extend loan via url: {extend_url}")
        try:
            response = self._br.open(extend_url)  # pylint: disable=assignment-from-none
        except mechanize.HTTPError as e:
            if e.code == 500:
                raise ExtendLoanError(f"Probably invalid extend loan URL: {extend_url}")
            else:
                raise e

        try:
            self._br.select_form(id="my-library-extend-loan-form")
        except mechanize.FormNotFoundError:
            raise IncompatibleSourceError("Can not find extend loan form", html_body="")

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
                raise ExtendLoanError(f"Could not extend loans using url: {extend_url}")
            else:
                raise e

        # disclaimer: not sure if other codes are realistic
        success = True if response.code == 200 else False

        # Try to add result details, but don't fail if we fail to parse details, it's tricky :-)
        try:
            # On submit, we arrive at "uitleningen" (loans) page, which lists the result
            html_string = response.read().decode("utf-8")
            # Path("response.html").write_text("html_string")  # for debugging
            details = self._parse_extend_response_page(html_string)
            if "likely_success" in details and details["likely_success"] is False:
                # Probably valid page (http=200) but with 'Foutmelding'
                success = False
        except Exception as e:
            _log.warning(f"Could not parse loan extending result. Error: {e}")
            details = {}

        return success, details

    # *** INTERNAL METHODS ***

    def _log_in(self, url):
        # NOTE:consider replacing with oauth-based authentication flow

        html_string_start_page = "not yet set"  # placeholder for troubleshooting
        try:
            _log.debug("Opening login page ... ")
            response = self._br.open(url)  # pylint: disable=assignment-from-none
            html_string_start_page = response.read().decode("utf-8")  # type:ignore
            self._br.select_form(nr=0)
            self._br["email"] = self._username
            self._br["password"] = self._pwd
            response = self._br.submit()  # pylint: disable=assignment-from-none
        except mechanize.FormNotFoundError:
            raise IncompatibleSourceError(
                "Can not find login form", html_body=html_string_start_page
            )
        except urllib.error.URLError as e:
            raise CanNotConnectError(f"Error while trying to log in at: {url}  ({str(e)})")
        return response

    def _validate_logged_in(self, response):
        _log.debug("Checking if login is successful ...")
        html_string = response.read().decode("utf-8") if response is not None else ""
        if "Profiel" not in html_string:
            if (
                "privacyverklaring is gewijzigd" in html_string
                or "akkoord met de privacyverklaring" in html_string
            ):
                raise AuthenticationError(
                    "Login not accepted (likely need to accept privacy statement again)"
                )
            else:
                raise AuthenticationError("Login not accepted")
        _log.debug("Login was successful")

    def _open_account_loans_page(self, acc_url: str) -> str:
        _log.debug(f"Opening page ({acc_url}) ... ")
        try:
            response = self._br.open(acc_url)  # pylint: disable=assignment-from-none
        except mechanize.HTTPError as e:
            if e.code == 500:
                # duh, server crashes on incorrect or nonexisting ID in the link
                raise AccessError(
                    f"Loans url can not be opened. Likely incorrect or "
                    f"nonexisting account ID in the url '{acc_url}'"
                ) from e
            raise AccessError(
                f"Loans url can not be opened. Reason unknown. Error: {e}"
            ) from e

        html = response.read().decode("utf-8") if response is not None else ""
        return html

    @classmethod
    def _parse_accounts_list_page(cls, html: str, base_url: str) -> list[Account]:
        """Return list of accounts

        >>> html_string = '''
        ... ...
        ... <div class="my-library-user-library-account-list js-accordion">
        ...     <div class="my-library-user-library-account-list__library">
        ...        <h2 class="my-library-user-library-account-list__title ui-accordion-header">
        ...            <div class="my-library-user-library-account-list__title-content">
        ...                Dijk92
        ...                 <span class="region-info">...</span>
        ...            </div>
        ...        </h2>
        ...        <div class="my-library-user-library-account-list__account">
        ...            <div class="my-library-user-library-account-list__basic-info">
        ...                <a href="/mijn-bibliotheek/lidmaatschappen/374047">
        ...                    <div class="my-library-user-library-account-list__name" data-hj-suppress="">Johny</div>
        ...                    <div class="my-library-user-library-account-list__city" data-hj-suppress=""></div>
        ...                </a>
        ...            </div>
        ...            <ul class="my-library-user-library-account-list__info">
        ...                ...
        ...                <li class="my-library-user-library-account-list__loans-link">
        ...                    <a href="/mijn-bibliotheek/lidmaatschappen/374047/uitleningen">Geen uitleningen</a></li>
        ...                <li class="my-library-user-library-account-list__holds-link">
        ...                    <a href="/mijn-bibliotheek/lidmaatschappen/384767/reservaties">5 reserveringen</a></li>
        ...                ...
        ...            </ul>
        ...            ...
        ...        </div>
        ...     </div>
        ... </div>
        ... ...
        ... '''
        >>> MijnBibliotheek._parse_accounts_list_page(html_string,"https://example.com") # doctest: +NORMALIZE_WHITESPACE
        [Account(library_name='Dijk92', user='Johny', id='374047', loans_count=0, loans_url='https://example.com/mijn-bibliotheek/lidmaatschappen/374047/uitleningen',
                 reservations_count=5, reservations_url='https://example.com/mijn-bibliotheek/lidmaatschappen/384767/reservaties',
                 open_amounts=0, open_amounts_url='')]
        >>> MijnBibliotheek._parse_accounts_list_page("","https://example.com")
        []
        """
        accounts = []
        soup = BeautifulSoup(html, "html.parser")

        library_divs = soup.find_all(
            "div", class_="my-library-user-library-account-list__library"
        )
        if not library_divs:
            _log.warning("No library accounts detected. Weird; expected at least 1.")

        for lib_div in library_divs:
            lib_title = (
                lib_div.find(
                    "div", class_="my-library-user-library-account-list__title-content"
                )
                .find(string=True, recursive=False)
                .get_text()
                .strip()
            )

            # Get accounts
            acc_divs = lib_div.find_all(
                "div", class_="my-library-user-library-account-list__account"
            )
            for acc_div in acc_divs:
                # TODO: get details from json object, see https://github.com/myTselection/bibliotheek_be/blob/fec95c3481f78d98062c1117627da652ec8d032d/custom_components/bibliotheek_be/utils.py#L145C53-L145C75
                # Get id from <a href="/mijn-bibliotheek/lidmaatschappen/374047">
                acc_id = acc_div.a["href"].strip().split("/")[3]

                acc_user = (
                    acc_div.find("div", class_="my-library-user-library-account-list__name")
                    .get_text()
                    .strip()
                )

                loans_count = cls._parse_item_count_from_li(
                    acc_div, "my-library-user-library-account-list__loans-link"
                )

                try:
                    loans_url = base_url + acc_div.find(
                        "a", href=re.compile("uitleningen")
                    ).get("href")
                except AttributeError:
                    loans_url = ""

                holds_count = cls._parse_item_count_from_li(
                    acc_div, "my-library-user-library-account-list__holds-link"
                )

                try:
                    holds_url = base_url + acc_div.find(
                        "a", href=re.compile("reservaties")
                    ).get("href")
                except AttributeError:
                    holds_url = ""

                try:
                    open_amounts = acc_div.find(
                        "li", class_="my-library-user-library-account-list__open-amount-link"
                    ).a.get_text()
                    if "geen" in open_amounts.lower():
                        open_amounts = 0
                    else:
                        # Copied from https://github.com/myTselection/bibliotheek_be
                        open_amounts = float(
                            open_amounts.lower()
                            .replace(" openstaande bedragen", "")
                            .replace(" openstaand bedrag", "")
                            .replace(" openstaande kosten", "")
                            .replace("€", "")
                            .replace(",", ".")
                        )
                except AttributeError:
                    open_amounts = 0

                try:
                    open_amounts_url = base_url + acc_div.find(
                        "a", href=re.compile("betalen")
                    ).get("href")
                except AttributeError:
                    open_amounts_url = ""

                account = Account(
                    id=acc_id,
                    library_name=lib_title,
                    user=acc_user,
                    loans_count=loans_count,
                    loans_url=loans_url,
                    reservations_count=holds_count,
                    reservations_url=holds_url,
                    open_amounts=open_amounts,
                    open_amounts_url=open_amounts_url,
                )
                accounts.append(account)
        return accounts

    @staticmethod
    def _parse_item_count_from_li(acc_div, class_: str) -> int | None:
        """Return None if no info found, otherwise return item count (potentially 0)"""
        item_count = None
        try:
            acc_a_text = acc_div.find("li", class_=class_).a.get_text().strip()
            if "Geen" in acc_a_text:  # 'Geen uitleningen' or 'Geen reservaties'
                item_count = 0
            else:
                numbers = [int(s) for s in acc_a_text.split() if s.isdigit()]
                if numbers:
                    item_count = numbers[0]
        except Exception:
            _log.warning("Unexpected html structure. Ignore item count")
        return item_count

    @classmethod
    def _parse_account_loan_page(cls, html: str, base_url: str) -> list[Loan]:
        """Return loans

        >>> html_string='''
        ... <div class="my-library-user-library-account-loans__loan-wrapper">
        ... <h2>Gent Hoofdbibiliotheek</h2>
        ...
        ... <div class="card my-library-user-library-account-loans__loan my-library-user-library-account-loans__loan-type-">
        ...     <div class="my-library-user-library-account-loans__loan-content card--content">
        ...     <div class="my-library-user-library-account-loans__loan-cover card--cover">
        ...         <img class="my-library-user-library-account-loans__loan-cover-img card--cover-img"
        ...         src="https://webservices.bibliotheek.be/index.php?func=cover&amp;ISBN=9789000359325&amp;VLACCnr=10157217&amp;CDR=&amp;EAN=&amp;ISMN=&amp;EBS=&amp;coversize=medium"
        ...         alt="Erebus">
        ...     </div>
        ...     <div class="my-library-user-library-account-loans__loan-intro card--intro">
        ...         <div
        ...         class="my-library-user-library-account-loans__loan-type-label card--type-label atalog-item-icon catalog-item-icon--book">
        ...         Boek</div>
        ...         <h3 class="my-library-user-library-account-loans__loan-title card--title"><a
        ...             href="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C1324927">Erebus</a></h3>
        ...     </div>
        ...     </div>
        ...     <div class="my-library-user-library-account-loans__loan-footer card--footer">
        ...     <div class="author">
        ...         Palin, Michael
        ...     </div>
        ...     <div class="my-library-user-library-account-loans__loan-days card--days ">
        ...         Nog 23 dagen
        ...     </div>
        ...     <div class="my-library-user-library-account-loans__loan-from-to card--from-to">
        ...         <div>
        ...         <span>Van</span>
        ...         <span>25/11/2023</span>
        ...         </div>
        ...         <div>
        ...         <span>Tot en met</span>
        ...         <span>23/12/2023</span>
        ...         </div>
        ...     </div>
        ...     <div class="my-library-user-library-account-loans__extend-loan card--extend-loan">
        ...         <div>
        ...         <input type="checkbox" id="6207416" value="6207416" data-renew-loan="">
        ...         <label for="6207416">Selecteren</label>
        ...         </div>
        ...         <a href="/mijn-bibliotheek/lidmaatschappen/374052/uitleningen/verlengen?loan-ids=6207416">Verleng</a>
        ...     </div>
        ...     </div>
        ... </div>
        ... </div>
        ... '''
        >>> MijnBibliotheek._parse_account_loan_page(html_string,"https://city.bibliotheek.be") # doctest: +NORMALIZE_WHITESPACE
        [Loan(title='Erebus', loan_from=datetime.date(2023, 11, 25), loan_till=datetime.date(2023, 12, 23),
            author='Palin, Michael', type='Boek', extendable=True,
            extend_url='https://city.bibliotheek.be/mijn-bibliotheek/lidmaatschappen/374052/uitleningen/verlengen?loan-ids=6207416',
            extend_id='6207416', branchname='Gent Hoofdbibiliotheek', id='1324927',
            url='https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C1324927',
            cover_url='https://webservices.bibliotheek.be/index.php?func=cover&ISBN=9789000359325&VLACCnr=10157217&CDR=&EAN=&ISMN=&EBS=&coversize=medium')]
        """
        loans = []
        soup = BeautifulSoup(html, "html.parser")

        loansection_div = soup.find(
            "div", class_="my-library-user-library-account-loans__loan-wrapper"
        )
        if not loansection_div:
            error_msg = (
                "Er is een fout opgetreden bij het ophalen van informatie uit het "
                "bibliotheeksysteem. Probeer het later opnieuw."
            )
            # Sometimes, this error is present
            if soup.find(string=re.compile(error_msg)) is not None:
                _log.warning(
                    f"Loans or reservations can not be retrieved. Site reports: {error_msg}"
                )
            return loans

        # Unfortunately, the branch names are interwoven siblings of the loans,
        # so we have to parse all items as we go along, and track branch name
        children = loansection_div.find_all(recursive=False)  # type:ignore
        branch_name = "??"
        for child in children:
            if child.name == "h2":  # we expect this to be the first child
                branch_name = child.get_text().strip()
                # TODO: check if this resolves to the same https://github.com/myTselection/bibliotheek_be/blob/fec95c3481f78d98062c1117627da652ec8d032d/custom_components/bibliotheek_be/utils.py#L306
            elif child.name == "div":  # loan div
                # we convert child soup object to string, so called function
                # can be used also easily for unit tests
                loan = cls._get_loan_info_from_div(str(child), branch_name, base_url)
                loans.append(loan)
            else:
                # should not happen, fail gracefully for now.
                _log.warning("Unexpected html structure. Did not find loan nor branch.")
        _log.debug("Number of loans found: %s", len(loans))
        return loans

    @classmethod
    def _get_loan_info_from_div(cls, loan_div_html: str, branch: str, base_url: str) -> Loan:
        """Return loan from html loan_div blob"""
        loan_div = BeautifulSoup(loan_div_html, "html.parser")
        loan = {}

        try:
            loan_a = loan_div.find(
                "h3", class_="my-library-user-library-account-loans__loan-title card--title"
            ).a
            loan["title"] = loan_a.get_text().strip()
            loan["url"] = loan_a["href"]
            # Since id is only used to differentiate between titles, use last id-like part from url
            # URL looks like 'https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C1144255'
            loan["id"] = loan_a["href"].encode("utf-8").split(b"%7C")[-1].decode("utf-8")
        except AttributeError:
            _log.warning("Unexpected html structure. Ignoring loan title, url and id")

        try:
            loan["author"] = loan_div.find("div", class_="author").get_text().strip()
        except AttributeError:
            loan["author"] = ""  # Likely, not all loans have an author

        try:
            loan["type"] = (
                loan_div.find(
                    "div", class_="my-library-user-library-account-loans__loan-type-label"
                )
                .get_text()
                .strip()
            )
        except AttributeError:
            loan["type"] = ""  # Not all loans have a type

        try:
            loan["cover_url"] = loan_div.find(
                "img", class_="my-library-user-library-account-loans__loan-cover-img"
            )["src"]
        except AttributeError:
            loan["cover_url"] = ""

        try:
            fromto_div = loan_div.find(
                "div",
                class_="my-library-user-library-account-loans__loan-from-to",
            )
            from_ = fromto_div.find_all("span")[1].get_text().strip()  # type:ignore
            to_ = fromto_div.find_all("span")[3].get_text().strip()  # type:ignore
            loan["loan_from"] = datetime.strptime(from_, cls.DATE_FORMAT).date()
            loan["loan_till"] = datetime.strptime(to_, cls.DATE_FORMAT).date()
        except AttributeError:
            _log.warning("Unexpected html structure. Ignoring loan start and end date")

        try:
            extend_loan_div = loan_div.find("div", class_="card--extend-loan")
            if extend_loan_div.get_text().strip() == "Verlengen niet mogelijk":
                loan["extendable"] = False
            else:
                loan["extendable"] = True
                extend_url = extend_loan_div.a["href"]  # type:ignore
                extend_url = urllib.parse.urljoin(base_url, extend_url)  # type:ignore
                loan["extend_url"] = extend_url
                loan["extend_id"] = extend_loan_div.input.get("id")
        except AttributeError:
            loan["extendable"] = None
            loan["extend_url"] = ""
            loan["extend_id"] = ""

        loan["branchname"] = branch

        return Loan(
            title=loan.get("title", ""),
            loan_from=loan.get("loan_from", None),
            loan_till=loan.get("loan_till", None),
            author=loan.get("author", ""),
            type=loan.get("type", ""),
            extendable=loan.get("extendable", None),
            extend_url=loan.get("extend_url", ""),
            extend_id=loan.get("extend_id", ""),
            branchname=loan.get("branchname", ""),
            id=loan.get("id", ""),
            url=loan.get("url", ""),
            cover_url=loan.get("cover_url", ""),
        )

    @classmethod
    def _parse_account_reservations_page(cls, html_string: str) -> list[Reservation]:
        """Return list of holds

        >>> html_string='''
        ... <div class="my-library-user-library-account-holds__hold-wrapper">
        ...   <div class="my-library-user-library-account-holds__hold card">
        ...     <div class="my-library-user-library-account-holds__hold-first card--first-section">
        ...       <p>Aangevraagd op 25/11/2023</p>
        ...       <p> Aanvraag geldig tot 24/11/2024</p>
        ...     </div>
        ...     <div class="my-library-user-library-account-holds__hold-second card--second-section">
        ...       <div class="catalog-item catalog-item--view-mode-small-teaser">
        ...         <div class="catalog-item__image">
        ...           <a href="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C12345"
        ...             target="_blank"><img
        ...               src="https://city.bibliotheek.be/themes/custom/library_portal_theme/assets/img/placeholder_book.png"
        ...               alt="Vastberaden!"></a>
        ...         </div>
        ...         <div class="catalog-item__content">
        ...           <h2 class="catalog-item__title">
        ...             <a href="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C12345"
        ...               target="_blank">Vastberaden!</a>
        ...           </h2>
        ...           <div class="catalog-item__authors">
        ...             John Doe
        ...           </div>
        ...         </div>
        ...       </div>
        ...     </div>
        ...     <div class="my-library-user-library-account-holds__hold-third card--third-section">
        ...       <p><i class="fa fa-map-marker" aria-hidden="true"></i> Locatie: <strong>MyCity</strong></p>
        ...     </div>
        ...     <div class="my-library-user-library-account-holds__hold-fourth card--fourth-section">
        ...       <h3><i class="fa fa-circle" aria-hidden="true"></i> Onderweg naar jouw bibliotheek</h3>
        ...       <p><i class="fa fa-bell" aria-hidden="true"></i> Je ontvangt een melding wanneer je reservering klaar is om af te
        ...         halen</p>
        ...     </div>
        ...   </div>
        ... </div>
        ... '''
        >>> MijnBibliotheek._parse_account_reservations_page(html_string) # doctest: +NORMALIZE_WHITESPACE
        [Reservation(title='Vastberaden!', type='', url='https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C12345',
            author='John Doe', location='MyCity', available=False, available_till=None,
            request_on=datetime.date(2023, 11, 25), valid_till=datetime.date(2024, 11, 24))]
        >>> MijnBibliotheek._parse_account_reservations_page("") # doctest: +NORMALIZE_WHITESPACE
        []
        """
        holds = []
        soup = BeautifulSoup(html_string, "html.parser")

        holds_section_div = soup.find(
            "div", class_="my-library-user-library-account-holds__hold-wrapper"
        )
        if not holds_section_div:
            return holds

        children = holds_section_div.find_all(recursive=False)  # type:ignore
        # child is "class==my-library-user-library-account-holds__hold card"
        for child in children:
            hold = {}

            try:
                hold["type"] = (
                    child.find("div", class_="catalog-item__content")
                    .find("span")
                    .get_text()
                    .strip()
                )
            except AttributeError:
                pass  # some holds don't have a type

            try:
                hold["request_on"] = (
                    child.find("p", string=re.compile("Aangevraagd op"))
                    .get_text()
                    .replace("Aangevraagd op ", "")
                    .strip()
                )
                hold["request_on"] = datetime.strptime(
                    hold["request_on"], cls.DATE_FORMAT
                ).date()
            except AttributeError:
                _log.warning("Unexpected html structure. Ignoring hold request date")

            try:
                hold["valid_till"] = (
                    child.find("p", string=re.compile("Aanvraag geldig tot"))
                    .get_text()
                    .replace("Aanvraag geldig tot ", "")
                    .strip()
                )
                hold["valid_till"] = datetime.strptime(
                    hold["valid_till"], cls.DATE_FORMAT
                ).date()
            except AttributeError:
                pass  # once available, date not present anymore

            try:
                hold_a = child.find("h2", class_="catalog-item__title").a
                hold["title"] = hold_a.get_text().strip()
                hold["url"] = hold_a["href"]
            except AttributeError:
                _log.warning("Unexpected html structure. Ignoring hold title and url")

            try:
                hold["author"] = (
                    child.find("div", class_="catalog-item__authors").get_text().strip()
                )
            except AttributeError:
                pass  # likely, not all items have an author

            try:
                hold_div = child.find(
                    "div",
                    class_="my-library-user-library-account-holds__hold-third card--third-section",
                )
                hold["location"] = hold_div.find("strong").get_text().strip()
            except AttributeError:
                _log.warning("Unexpected html structure. Ignoring hold location.")

            try:
                hold_div = child.find(
                    "div",
                    class_="my-library-user-library-account-holds__hold-fourth card--fourth-section",
                )
                hold["available"] = (
                    "Klaar om af te halen" in hold_div.find("h3").get_text().strip()
                )
                if hold["available"] is True:
                    date_info_end = hold_div.find("strong").get_text().strip()
                    hold["endavailable"] = datetime.strptime(
                        date_info_end, cls.DATE_FORMAT
                    ).date()
            except AttributeError:
                _log.warning("Unexpected html structure. Ignoring hold availability.")

            reservation = Reservation(
                title=hold.get("title", ""),
                type=hold.get("type", ""),
                url=hold.get("url", ""),
                author=hold.get("author", ""),
                location=hold.get("location", ""),
                available=hold.get("available", False),
                available_till=hold.get("endavailable", None),
                request_on=hold.get("request_on", None),
                valid_till=hold.get("valid_till", None),
            )
            holds.append(reservation)
        _log.debug("Number of holds found: %s", len(holds))
        return holds

    @classmethod
    def _parse_extend_response_page(cls, html_string: str) -> dict:
        """For dict structure, see the called method"""
        html_blob = cls._extract_html_from_response_script_tag(html_string)
        return cls._parse_extend_response_status_blob(html_blob)

    @staticmethod
    def _extract_html_from_response_script_tag(raw_html: str):
        """
        The extending loan response contains the result in a ajax script thingy.
        This function extracts the part we are interested in and returns the decoded html.

        See the tests for an example.
        """

        def find_between(s: str, start: str, end: str):
            return s[s.find(start) + len(start) : s.rfind(end)]

        # find relevant snippet
        soup = BeautifulSoup(raw_html, "html.parser")
        script_txt = soup.find(
            "script", string=re.compile("(Statusbericht|Foutmelding)")
        ).get_text()
        script_txt = find_between(script_txt, '"data":"', '","settings')

        # decode
        html_blob = script_txt.replace(r"\/", "/")
        html_blob = bytes(html_blob, "ascii").decode("unicode_escape")

        return html_blob

    @classmethod
    def _parse_extend_response_status_blob(cls, html_string: str) -> dict:
        """Return details on loans that where extended succesfully

        >>> html_string = '''
        ... <div role="contentinfo" aria-label="Statusbericht" class="messages messages--status"
        ...  ... >
        ...  <i class="icon fa fa-exclamation-triangle" aria-hidden="true"></i>
        ...  <h2 class="visually-hidden">Statusbericht</h2>
        ...  <ul class="messages__list">
        ...    <li class="messages__item">Deze uitleningen werden succesvol verlengd:</li>
        ...    <li class="messages__item">"<em class="placeholder">Vastberaden!</em>" tot 13/01/2024.</li>
        ...    <li class="messages__item">"<em class="placeholder">Iemand moet het doen</em>" tot 13/01/2024.</li>
        ...  </ul>
        ... </div>
        ... '''
        >>> MijnBibliotheek._parse_extend_response_status_blob(html_string) # doctest: +NORMALIZE_WHITESPACE
        {'likely_success': True, 'count': 2, 'details':
            [{'title': 'Vastberaden!', 'until': datetime.date(2024, 1, 13)},
             {'title': 'Iemand moet het doen', 'until': datetime.date(2024, 1, 13)}]}
        >>> MijnBibliotheek._parse_extend_response_status_blob("")
        {'likely_success': False, 'count': 0, 'details': []}
        """
        # NOTE: Unclear when & what response when no success (500 server crash on most tests with
        #       different IDs and combinations)
        # If trying to extend loan which has already been extended, there is a red message saying
        # "Er ging iets fout bij het verlengen"
        count = 0
        details = []
        success = False
        soup = BeautifulSoup(html_string, "html.parser")
        try:
            msg_lis = soup.find("ul", class_="messages__list").find_all("li")  # type:ignore
            if msg_lis and "werden succesvol verlengd" in msg_lis[0].get_text():
                success = True
                count = len(msg_lis) - 1
                for li in msg_lis[1:]:
                    until = li.get_text().rsplit(" ", 1)[-1].strip(".")
                    until = datetime.strptime(until, cls.DATE_FORMAT).date()
                    details.append({"title": li.em.get_text(), "until": until})
            if msg_lis and "Er ging iets fout bij het verlengen" in msg_lis[0].get_text():
                # Probably, messages could be mix of success and failures. However, unclear.
                # So, just play safe and report it was no success at all
                count = 0
                success = False
        except AttributeError:
            _log.warning("Unexpected html structure. Reporting 0 extensions; could be wrong")

        return {"likely_success": success, "count": count, "details": details}


@dataclass
class Loan:
    title: str = ""
    loan_from: date | None = None
    loan_till: date | None = None
    author: str = ""
    type: str = ""
    extendable: bool | None = None
    extend_url: str = ""  # empty when `extendable` is False or None
    extend_id: str = ""  # can be used as input to extend multiple loans
    branchname: str = ""
    id: str = ""
    url: str = ""
    cover_url: str = ""
    # TODO: add account_id (Also needed for extending multiple loans)


@dataclass
class Reservation:
    title: str
    type: str
    url: str
    author: str
    location: str
    available: bool
    available_till: date | None = None
    request_on: date | None = None
    valid_till: date | None = None


@dataclass
class Account:
    library_name: str
    user: str
    id: str
    loans_count: int | None
    loans_url: str
    reservations_count: int | None
    reservations_url: str
    open_amounts: float
    open_amounts_url: str
