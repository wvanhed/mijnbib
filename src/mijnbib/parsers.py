from __future__ import annotations

import logging
import re
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from mijnbib.errors import TemporarySiteError
from mijnbib.models import Loan, Reservation

_log = logging.getLogger(__name__)

DATE_FORMAT = "%d/%m/%Y"

# CHEAT SHEET - BeautifulSoup (aka, things I always forget)
#
# .get_text()   It returns all the text in a document or beneath a tag, as a
#               single Unicode string. Probably preferred over .string
# .text         Seems to be shorthand for .get_text().
# .string       Typically returns the single string withing a tag, but can also
#               return None, or the string from the single-containing tag. It's
#               complicated, see also https://stackoverflow.com/a/25328374/50899


class Parser(ABC):
    @abstractmethod
    def parse(self, html: str, *args, **kwargs) -> Any:
        pass


class LoansListPageParser(Parser):
    def parse(self, html: str, base_url: str, account_id: str) -> list[Loan]:
        """Return loans.

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
        ...         <a href="/mijn-bibliotheek/lidmaatschappen/123456/uitleningen/verlengen?loan-ids=6207416">Verleng</a>
        ...     </div>
        ...     </div>
        ... </div>
        ... </div>
        ... '''
        >>> LoansListPageParser().parse(html_string,"https://city.bibliotheek.be","123456") # doctest: +NORMALIZE_WHITESPACE
        [Loan(title='Erebus', loan_from=datetime.date(2023, 11, 25), loan_till=datetime.date(2023, 12, 23),
            author='Palin, Michael', type='Boek', extendable=True,
            extend_url='https://city.bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/uitleningen/verlengen?loan-ids=6207416',
            extend_id='6207416', branchname='Gent Hoofdbibiliotheek', id='1324927',
            url='https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C1324927',
            cover_url='https://webservices.bibliotheek.be/index.php?func=cover&ISBN=9789000359325&VLACCnr=10157217&CDR=&EAN=&ISMN=&EBS=&coversize=medium',
            account_id='123456')]
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
                raise TemporarySiteError(
                    f"Loans or reservations can not be retrieved. Site reports: {error_msg}"
                )
                # _log.warning(
                #     f"Loans or reservations can not be retrieved. Site reports: {error_msg}"
                # )
            return loans

        # Unfortunately, the branch names are interwoven siblings of the loans,
        # so we have to parse all items as we go along, and track branch name
        children = loansection_div.find_all(recursive=False)  # type:ignore
        branch_name = "??"
        for child in children:
            if child.name == "h2":  # we expect this to be the first child
                branch_name = child.get_text().strip()
            elif child.name == "div":  # loan div
                # we convert child soup object to string, so called function
                # can be used also easily for unit tests
                loan = self._get_loan_info_from_div(
                    str(child), base_url, branch_name, account_id
                )
                loans.append(loan)
            else:
                # should not happen, fail gracefully for now.
                _log.warning("Unexpected html structure. Did not find loan nor branch.")
        _log.debug("Number of loans found: %s", len(loans))
        return loans

    @staticmethod
    def _get_loan_info_from_div(
        loan_div_html: str, base_url: str, branch: str, acc_id: str
    ) -> Loan:
        """Return loan from html loan_div blob."""
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
            loan["loan_from"] = datetime.strptime(from_, DATE_FORMAT).date()
            loan["loan_till"] = datetime.strptime(to_, DATE_FORMAT).date()
        except AttributeError:
            _log.warning("Unexpected html structure. Ignoring loan start and end date")

        try:
            extend_loan_div = loan_div.find("div", class_="card--extend-loan")
            if extend_loan_div.get_text().strip() == "Verlengen niet mogelijk":
                loan["extendable"] = False
            elif extend_loan_div and extend_loan_div.find("a"):
                # Case 1: UI where "Verleng" button is present
                loan["extendable"] = True
                extend_url = extend_loan_div.a.get("href")  # type:ignore
                extend_url = urllib.parse.urljoin(base_url, extend_url)  # type:ignore
                loan["extend_url"] = extend_url
                # loan["extend_id"] = extend_loan_div.input.get("id")
                loan["extend_id"] = extend_url.split("loan-ids=")[1]
            else:
                # Case 2: UI where "Verleng" button is NOT present
                loan["extendable"] = True
                extend_id = extend_loan_div.input.get("id")
                extend_url = (
                    f"/mijn-bibliotheek/lidmaatschappen/{acc_id}/uitleningen/verlengen"
                    + f"?loan-ids={extend_id}"
                )
                extend_url = urllib.parse.urljoin(base_url, extend_url)
                loan["extend_url"] = extend_url
                loan["extend_id"] = extend_id
        except (AttributeError, IndexError):
            # Note: IndexError is for extend_id handling from case 1
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
            account_id=acc_id,
        )


class ReservationsPageParser(Parser):
    def parse(self, html: str) -> list[Reservation]:
        """Return list of holds.

        >>> html_string='''
        ... <div class="my-library-user-library-account-holds__hold-wrapper">
        ...   <div class="my-library-user-library-account-holds__hold card">
        ...     <div class="my-library-user-library-account-holds__hold-first card--first-section">
        ...       <p>Aangevraagd op 25/11/2023</p>
        ...       <p> Aanvraag geldig tot 24/11/2024</p>
        ...     </div>
        ...     <div class="my-library-user-library-account-holds__hold-second card--second-section">
        ...       <div class="catalog-item-small-teaser">
        ...         <div class="catalog-item-small-teaser__image">
        ...           <a href="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C12345"
        ...             target="_blank" title="Vastberaden!"><img
        ...               src="https://city.bibliotheek.be/themes/custom/library_portal_theme/assets/img/placeholder_book.png"
        ...               alt="Vastberaden!"></a>
        ...         </div>
        ...          <div class="catalog-item-small-teaser__content">
        ...           <h2 class="catalog-item-small-teaser__title">
        ...             <a href="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C12345"
        ...               target="_blank">Vastberaden!</a>
        ...           </h2>
        ...           <div class="catalog-item-small-teaser__authors">
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
        >>> ReservationsPageParser().parse(html_string) # doctest: +NORMALIZE_WHITESPACE
        [Reservation(title='Vastberaden!', type='', url='https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C12345',
            author='John Doe', location='MyCity', available=False, available_till=None,
            request_on=datetime.date(2023, 11, 25), valid_till=datetime.date(2024, 11, 24))]
        """
        holds = []
        soup = BeautifulSoup(html, "html.parser")

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
                    child.find("div", class_="catalog-item-small-teaser__content")
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
                hold["request_on"] = datetime.strptime(hold["request_on"], DATE_FORMAT).date()
            except AttributeError:
                _log.warning("Unexpected html structure. Ignoring hold request date")

            try:
                hold["valid_till"] = (
                    child.find("p", string=re.compile("Aanvraag geldig tot"))
                    .get_text()
                    .replace("Aanvraag geldig tot ", "")
                    .strip()
                )
                hold["valid_till"] = datetime.strptime(hold["valid_till"], DATE_FORMAT).date()
            except AttributeError:
                pass  # once available, date not present anymore

            try:
                hold_a = child.find("h2", class_="catalog-item-small-teaser__title").a
                hold["title"] = hold_a.get_text().strip()
                hold["url"] = hold_a["href"]
            except AttributeError:
                _log.warning("Unexpected html structure. Ignoring hold title and url")

            try:
                hold["author"] = (
                    child.find("div", class_="catalog-item-small-teaser__authors")
                    .get_text()
                    .strip()
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
                    hold["endavailable"] = datetime.strptime(date_info_end, DATE_FORMAT).date()
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


class ExtendResponsePageParser(Parser):
    def parse(self, html) -> dict:
        """For dict structure, see the called method."""
        html_blob = self._extract_html_from_response_script_tag(html)
        return self._parse_extend_response_status_blob(html_blob)

    @staticmethod
    def _extract_html_from_response_script_tag(html: str):
        """Return html-encoded data from ajax encoded data.

        The extending loan response contains the result in a ajax script thingy.
        This function extracts the part we are interested in and returns the decoded html.
        See the tests for an example.
        """

        def find_between(s: str, start: str, end: str):
            # find_between("aabbcc", "aa", "cc") returns "bb"
            return s[s.find(start) + len(start) : s.rfind(end)]

        # find relevant snippet
        soup = BeautifulSoup(html, "html.parser")
        script_txt = soup.find(
            "script", string=re.compile("(Statusbericht|Foutmelding)")
        ).get_text()
        script_txt = find_between(script_txt, '"data":"', '","settings')

        # decode
        html_blob = script_txt.replace(r"\/", "/")
        html_blob = bytes(html_blob, "ascii").decode("unicode_escape")

        return html_blob

    @staticmethod
    def _parse_extend_response_status_blob(html_string: str) -> dict:
        """Return details on loans that where extended succesfully.

        >>> html_string = '''
        ... <div role="contentinfo" aria-label="Statusbericht" class="messages messages--status">
        ...   <i class="icon fa-solid fa-check" aria-hidden="true"></i>
        ...   <div role="alert">
        ...     <div class="messages--text">
        ...       <h2 class="visually-hidden">Statusbericht</h2>
        ...       <p>Deze uitleningen werden succesvol verlengd:</p>
        ...       <ul>
        ...         <li>"<em class="placeholder">Boek titel 1</em>" tot 13/01/2024.</li>
        ...         <li>"<em class="placeholder">Boek titel 2</em>" tot 13/01/2025.</li>
        ...       </ul>
        ...     </div>
        ...   </div>
        ... </div>
        ... '''
        >>> ExtendResponsePageParser._parse_extend_response_status_blob(html_string) # doctest: +NORMALIZE_WHITESPACE
        {'likely_success': True, 'count': 2, 'extension_info':
            [{'title': 'Boek titel 1', 'until': datetime.date(2024, 1, 13)},
             {'title': 'Boek titel 2', 'until': datetime.date(2025, 1, 13)}]}
        """
        # NOTE: Unclear when & what response when no success (500 server crash on most tests with
        #       different IDs and combinations)
        count = 0
        extension_info = []
        success = False
        soup = BeautifulSoup(html_string, "html.parser")
        try:
            div = soup.find("div", class_="messages--text")
            lis = div.find_all("li")  # type:ignore
            if lis and "werden succesvol verlengd" in div.p.get_text():  # type:ignore
                success = True
                count = len(lis)
                for li in lis:
                    until = li.get_text().rsplit(" ", 1)[-1].strip(".")
                    until = datetime.strptime(until, DATE_FORMAT).date()
                    extension_info.append({"title": li.em.get_text(), "until": until})  # type:ignore
            if lis and "Er ging iets fout bij het verlengen" in lis[0].get_text():
                # Probably, messages could be mix of success and failures. However, unclear.
                # So, just play safe and report it was no success at all
                count = 0
                success = False
        except AttributeError as e:
            _log.debug(f"Could not parse extend response status blob: {e}")
            _log.warning("Unexpected html structure. Reporting 0 extensions; could be wrong")

        return {"likely_success": success, "count": count, "extension_info": extension_info}
