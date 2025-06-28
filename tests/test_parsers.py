import datetime

from mijnbib.models import Loan
from mijnbib.parsers import (
    ExtendResponsePageParser,
    LoansListPageParser,
    ReservationsPageParser,
)

class TestLoansListPageParser:
    def test_parse_account_loans_page(self):
        # Happy flow test --> see doctest
        assert LoansListPageParser().parse(html="", base_url="", account_id="") == []
        assert LoansListPageParser().parse(html="bogus", base_url="", account_id="") == []

    def test_parse_account_loans_new_extend_ui(self):
        html_string = """
            <div class="my-library-user-library-account-loans__loan-wrapper">
              <h2>Gent Hoofdbibliotheek</h2>

              <div class="card my-library-user-library-account-loans__loan my-library-user-library-account-loans__loan-type-">

                <div class="my-library-user-library-account-loans__loan-content card--content">
                  <div class="my-library-user-library-account-loans__loan-cover card--cover">
                    <img class="my-library-user-library-account-loans__loan-cover-img card--cover-img"
                      src="https://webservices.bibliotheek.be/index.php?func=cover&amp;ISBN=1234567890123&amp;VLACCnr=12345678&amp;CDR=&amp;EAN=&amp;ISMN=&amp;EBS=&amp;coversize=medium"
                      alt="Een willekeurige boektitel" />
                  </div>
                  <div class="my-library-user-library-account-loans__loan-intro card--intro">
                    <div
                      class="my-library-user-library-account-loans__loan-type-label card--type-label atalog-item-icon catalog-item-icon--book">
                      Boek</div>
                    <h3 class="my-library-user-library-account-loans__loan-title card--title"><a
                        href="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C4690970">Een willekeurige boektitel</a></h3>
                  </div>
                </div>
                <div class="my-library-user-library-account-loans__loan-footer card--footer">

                  <div class="author">
                    Doe, John
                  </div>

                  <div class="my-library-user-library-account-loans__loan-days card--days ">
                    Nog 16 dagen
                  </div>

                  <div class="my-library-user-library-account-loans__loan-from-to card--from-to">
                    <div>
                      <span>Van</span>
                      <span>15/01/2025</span>
                    </div>
                    <div>
                      <span>Tot en met</span>
                      <span>12/02/2025</span>
                    </div>
                  </div>

                  <div class="my-library-user-library-account-loans__extend-loan card--extend-loan">
                    <div>
                      <input type="checkbox" id="abc123" value="abc123" data-renew-loan />
                      <label for="abc123">Selecteer om te verlengen</label>
                    </div>

                  </div>
                </div>
              </div>
            </div>
        """
        assert LoansListPageParser().parse(
            html=html_string, base_url="https://city.bibliotheek.be", account_id="account123"
        ) == [
            Loan(
                title="Een willekeurige boektitel",
                loan_from=datetime.date(2025, 1, 15),
                loan_till=datetime.date(2025, 2, 12),
                author="Doe, John",
                type="Boek",
                extendable=True,
                extend_url="https://city.bibliotheek.be/mijn-bibliotheek/lidmaatschappen/account123/uitleningen/verlengen?loan-ids=abc123",
                extend_id="abc123",
                branchname="Gent Hoofdbibliotheek",
                id="4690970",
                url="https://city.bibliotheek.be/resolver.ashx?extid=%7Cwise-oostvlaanderen%7C4690970",
                cover_url="https://webservices.bibliotheek.be/index.php?func=cover&ISBN=1234567890123&VLACCnr=12345678&CDR=&EAN=&ISMN=&EBS=&coversize=medium",
                account_id="account123",
            )
        ]


class TestReservationsPageParser:
    def test_parse_account_reservations_page(self):
        # Happy flow test --> see doctest
        assert ReservationsPageParser().parse("") == []
        assert ReservationsPageParser().parse("bogus") == []


class TestExtendResponsePageParser:
    def test_extract_html_from_response_script_tag(self):
        raw_html = r"""
        ...
        <script type="application/vnd.drupal-ajax"
        data-big-pipe-replacement-for-placeholder-with-id="callback=Drupal%5CCore%5CRender%5CElement%5CStatusMessages%3A%3ArenderMessages&amp;args%5B0%5D&amp;token=_HAdUpwWmet0TOTe2PSiJuMntExoshbm1kh2wQzzzAA">
        [{"command":"insert","method":"replaceWith","selector":"[data-big-pipe-placeholder-id=\u0022callback=Drupal%5CCore%5CRender%5CElement%5CStatusMessages%3A%3ArenderMessages\u0026args%5B0%5D\u0026token=_HAdUpwWmet0TOTe2PSiJuMntExoshbm1kh2wQzzzAA\u0022]","data":"\u003Cdiv data-drupal-messages\u003E\n                  \u003Cdiv role=\u0022contentinfo\u0022 aria-label=\u0022Statusbericht\u0022 class=\u0022messages messages--status\u0022\u003E\n        \u003Ci class=\u0022icon fa fa-exclamation-triangle\u0022 aria-hidden=\u0022true\u0022\u003E\u003C\/i\u003E\n                              \u003Ch2 class=\u0022visually-hidden\u0022\u003EStatusbericht\u003C\/h2\u003E\n                                \u003Cul class=\u0022messages__list\u0022\u003E\n                              \u003Cli class=\u0022messages__item\u0022\u003EDeze uitleningen werden succesvol verlengd:\u003C\/li\u003E\n                              \u003Cli class=\u0022messages__item\u0022\u003E\u0022\u003Cem class=\u0022placeholder\u0022\u003EHet schip der doden\u003C\/em\u003E\u0022 tot 08\/01\/2024.\u003C\/li\u003E\n                          \u003C\/ul\u003E\n                          \u003C\/div\u003E\n                  \u003C\/div\u003E\n","settings":null}]
        </script>
        ...
        """

        expected_result = """
            <div data-drupal-messages>
                <div role="contentinfo" aria-label="Statusbericht" class="messages messages--status">
                    <i class="icon fa fa-exclamation-triangle" aria-hidden="true"></i>
                    <h2 class="visually-hidden">Statusbericht</h2>
                    <ul class="messages__list">
                    <li class="messages__item">Deze uitleningen werden succesvol verlengd:</li>
                    <li class="messages__item">"<em class="placeholder">Het schip der doden</em>" tot 08/01/2024.</li>
                    </ul>
                </div>
            </div>
            """

        def clean_whitespace(s: str) -> str:
            return s.replace(" ", "").replace("\n", "")

        actual_result = ExtendResponsePageParser._extract_html_from_response_script_tag(
            raw_html
        )
        assert clean_whitespace(actual_result) == clean_whitespace(expected_result)

    def test_parse_extend_response_status_blob__empty_case(self):
        assert ExtendResponsePageParser._parse_extend_response_status_blob("") == {
            "likely_success": False,
            "count": 0,
            "details": [],
        }

    def test_parse_extend_response_status_blob__success_case(self):
        html_string = """
          <div data-drupal-messages>
            <div role="contentinfo" aria-label="Statusbericht" class="messages messages--status">
              <i class="icon fa fa-exclamation-triangle" aria-hidden="true"></i>
              <h2 class="visually-hidden">Statusbericht</h2>
              <ul class="messages__list">
                <li class="messages__item">Deze uitleningen werden succesvol verlengd:</li>
                <li class="messages__item">"<em class="placeholder">Het schip der doden</em>" tot 08/01/2024.</li>
              </ul>
            </div>
          </div>
        """

        actual_result = ExtendResponsePageParser._parse_extend_response_status_blob(
            html_string
        )
        assert actual_result == {
            "likely_success": True,
            "count": 1,
            "details": [{"title": "Het schip der doden", "until": datetime.date(2024, 1, 8)}],
        }

    def test_parse_extend_response_status_blob__foutmelding_case(self):
        html_string = """
          <div data-drupal-messages="">
            <div role="contentinfo" aria-label="Foutmelding" class="messages messages--error"
              data-gtm-vis-recent-on-screen9349158_360="48" data-gtm-vis-first-on-screen9349158_360="48"
              data-gtm-vis-total-visible-time9349158_360="100" data-gtm-vis-has-fired9349158_360="1">
              <i class="icon fa fa-exclamation-triangle" aria-hidden="true"></i>
              <div role="alert">
                <h2 class="visually-hidden">Foutmelding</h2>
                <ul class="messages__list">
                  <li class="messages__item">Er ging iets fout bij het verlengen van deze uitleningen:</li>
                  <li class="messages__item"><strong>"<em class="placeholder">De Helvetii</em>"</strong><br>Reden: Er ging iets
                    fout, gelieve het later opnieuw te proberen.</li>
                </ul>
              </div>
            </div>
          </div>
        """

        actual_result = ExtendResponsePageParser._parse_extend_response_status_blob(
            html_string
        )
        assert actual_result == {
            "likely_success": False,
            "count": 0,
            "details": [],
        }
