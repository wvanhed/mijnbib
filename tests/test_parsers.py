import datetime

from mijnbib.parsers import (
    AccountsListPageParser,
    ExtendResponsePageParser,
    LoansListPageParser,
    ReservationsPageParser,
)


class TestAccountsListPageParser:
    def test_parse_accounts_list_page(self):
        # Happy flow test --> see doctest
        assert AccountsListPageParser().parse("", "https://example.com") == []

    def test_parse_item_count_from_li(self):
        assert AccountsListPageParser._parse_item_count_from_li("", "") is None
        assert AccountsListPageParser._parse_item_count_from_li("bogus", "") is None


class TestLoansListPageParser:
    def test_parse_account_loans_page(self):
        # Happy flow test --> see doctest
        assert LoansListPageParser().parse(html="", base_url="", account_id="") == []
        assert LoansListPageParser().parse(html="bogus", base_url="", account_id="") == []


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
