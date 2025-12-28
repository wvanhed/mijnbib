from __future__ import annotations

import configparser
import logging
import warnings
from pathlib import Path

import pytest

from mijnbib import MijnBibliotheek
from mijnbib.errors import AuthenticationError, IncompatibleSourceError, ItemAccessError
from mijnbib.login_handlers import LoginByOAuth
from mijnbib.mijnbibliotheek import get_item_info
from mijnbib.models import Account, Loan, Reservation

CONFIG_FILE = "mijnbib.ini"


@pytest.fixture
def creds_config(scope="module"):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return dict(**config.defaults())


class TestLoginByOption:
    def test_login_by_options_default_is_by_oauth(self):
        mb = MijnBibliotheek("user", "pwd")
        assert mb._login_handler_class == LoginByOAuth

    def test_login_by_options_by_oauth(self):
        mb = MijnBibliotheek("user", "pwd", login_by="oauth")
        assert mb._login_handler_class == LoginByOAuth

    def test_login_by_options_invalid_option_raises_error(self):
        with pytest.raises(
            ValueError, match=r".*login_by needs to be either 'oauth' or 'form'.*"
        ):
            MijnBibliotheek("user", "pwd", login_by="foo")

    def test_login_by_options_by_form_warns_deprecation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mb = MijnBibliotheek("user", "pass", login_by="form")
            assert any(
                issubclass(warning.category, DeprecationWarning)
                and "'form' login_by option is deprecated" in str(warning.message)
                for warning in w
            )
            assert mb._login_handler_class == LoginByOAuth


class TestCustomParser:
    def test_loans_page_parser_can_be_overridden(self, requests_mock):
        # Arrange
        class MyCustomLoanParser:
            def parse(self, _html, _base_url, _account_id):
                return [Loan("some title")]

        mb = MijnBibliotheek("user", "pwd")
        # Fake both (a) valid login, and (b) some reponse on fetching loans page
        mb._logged_in = True
        requests_mock.get(
            "https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/whatever/uitleningen",
            text="doesn't matter what is here",
        )

        # Act
        mb._loans_page_parser = MyCustomLoanParser()  # type:ignore

        # Assert
        assert mb.get_loans(account_id="whatever") == [Loan("some title")]

    def test_reservations_parser_can_be_overridden(self, requests_mock):
        # Arrange
        res = Reservation("title", "dvd", "some_url", "author", "brussels", True)

        class MyCustomReservationsParser:
            def parse(self, _html):
                return [res]

        mb = MijnBibliotheek("user", "pwd")
        # Fake both (a) valid login, and (b) some reponse on fetching reservations page
        mb._logged_in = True
        requests_mock.get(
            "https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/whatever/reservaties",
            text="doesn't matter what is here",
        )

        # Act
        mb._reservations_parser = MyCustomReservationsParser()  # type:ignore

        # Assert
        assert mb.get_reservations(account_id="whatever") == [res]

    # def test_extendresponse_parser_can_be_overridden(self):
    # Not so easy to write test for


class TestGetAccounts:
    def test_get_accounts(self, requests_mock, caplog):
        mb = MijnBibliotheek("user", "pwd")
        mb._logged_in = True  # fake logged in
        requests_mock.get(
            "https://bibliotheek.be/mijn-bibliotheek/aanmelden?destination=/mijn-bibliotheek/lidmaatschappen",
            text="doesn't matter what is here",
        )
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/memberships",
            text="""
                {
                  "Dijk92": {
                    "region": {
                      "111111111111": [
                        {
                          "hasError": false,
                          "id": "123456",
                          "isBlocked": false,
                          "isExpired": false,
                          "libraryName": "Dijk92 - Bibliotheek Gent",
                          "library": "https://gent.bibliotheek.be",
                          "name": "John Doe"
                        },
                        {
                          "hasError": false,
                          "id": "456789",
                          "isBlocked": false,
                          "isExpired": false,
                          "libraryName": "Dijk92 - Bibliotheek Sint-Amandsberg",
                          "library": "https://sintamandsberg.bibliotheek.be",
                          "name": "John Doe"
                        }
                      ],
                      "22222222222": [
                        {
                          "hasError": true,
                          "id": "111222",
                          "isBlocked": false,
                          "isExpired": false,
                          "libraryName": "Dijk92 - Bibliotheek Gent",
                          "library": "https://gent.bibliotheek.be",
                          "name": "Jane Smith"
                        }
                      ]
                    }
                  }
                }
                """,
        )
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/123456/activities",
            text="""
                    {
                    "loanHistoryUrl": "/mijn-bibliotheek/lidmaatschappen/123456/leenhistoriek",
                    "numberOfHolds": 2,
                    "numberOfLoans": 5,
                    "openAmount": "3,20"
                    }
                """,
        )
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/456789/activities",
            text="""
                    {
                    "loanHistoryUrl": "/mijn-bibliotheek/lidmaatschappen/456789/leenhistoriek",
                    "numberOfHolds": 0,
                    "numberOfLoans": 1,
                    "openAmount": "0,00"
                    }
                """,
        )
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/111222/activities",
            text="""
                    {
                    "loanHistoryUrl": "/mijn-bibliotheek/lidmaatschappen/123456/leenhistoriek",
                    "numberOfHolds": 1,
                    "numberOfLoans": 1,
                    "openAmount": "5,00"
                    }
                """,
        )

        accounts = mb.get_accounts()

        # caplog.set_level(logging.WARNING)
        assert "Account 111222 reports error, skipping counts and amounts" in caplog.text

        assert len(accounts) == 3
        assert accounts[0] == Account(
            library_name="Dijk92 - Bibliotheek Gent",
            id="123456",
            user="John Doe",
            open_amounts=3.20,
            loans_count=5,
            reservations_count=2,
            loans_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/uitleningen",
            reservations_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/reservaties",
            open_amounts_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/te-betalen",
        )
        assert accounts[1] == Account(
            library_name="Dijk92 - Bibliotheek Sint-Amandsberg",
            id="456789",
            user="John Doe",
            open_amounts=0.0,
            loans_count=1,
            reservations_count=0,
            loans_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/456789/uitleningen",
            reservations_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/456789/reservaties",
            open_amounts_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/456789/te-betalen",
        )
        # # Note: 3nd account has `hasError` set to True, so some values are None
        assert accounts[2] == Account(
            library_name="Dijk92 - Bibliotheek Gent",
            id="111222",
            user="Jane Smith",
            open_amounts=0.00,  # 0 instead of 5.00,
            loans_count=None,  # must be None instead 1
            reservations_count=None,  # must be None instead 1
            loans_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/111222/uitleningen",
            reservations_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/111222/reservaties",
            open_amounts_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/111222/te-betalen",
        )

    def test_get_accounts_raises_incompatiblesource_error_on_unexpected_json_for_memberships(
        self, requests_mock
    ):
        mb = MijnBibliotheek("user", "pwd")
        mb._logged_in = True  # fake logged in
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/memberships",
            text="""
                    {
                      "Dijk92": {
                        "region": {
                          "111111111111": [
                            {
                              "not": "good"
                            }
                          ]
                        }
                      }
                    }
                """,
        )

        with pytest.raises(IncompatibleSourceError, match=r".*Was expecting key 'hasError'.*"):
            _accounts = mb.get_accounts()

    def test_get_accounts_raises_incompatiblesource_error_on_invalid_json_for_memberships(
        self, requests_mock
    ):
        mb = MijnBibliotheek("user", "pwd")
        mb._logged_in = True  # fake logged in
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/memberships",
            text="""
                    {
                    this is invalid json
                    }
                """,
        )

        with pytest.raises(IncompatibleSourceError, match=r".*JSONDecodeError.*"):
            _accounts = mb.get_accounts()

    def test_get_accounts_raises_incompatiblesource_error_on_invalid_json_for_activity(
        self, requests_mock
    ):
        mb = MijnBibliotheek("user", "pwd")
        mb._logged_in = True  # fake logged in
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/memberships",
            text="""
                {
                  "Dijk92": {
                    "region": {
                      "111111111111": [
                        {
                          "hasError": false,
                          "id": "123456",
                          "isBlocked": false,
                          "isExpired": false,
                          "libraryName": "Dijk92 - Bibliotheek Gent",
                          "library": "https://gent.bibliotheek.be",
                          "name": "John Doe"
                        }
                      ]
                    }
                  }
                }
                """,
        )
        requests_mock.get(
            "https://bibliotheek.be/api/my-library/123456/activities",
            text="""
                    {
                    this is invalid json
                    }
                """,
        )

        with pytest.raises(IncompatibleSourceError, match=r".*JSONDecodeError.*"):
            _accounts = mb.get_accounts()


@pytest.mark.real
@pytest.mark.skipif(
    not Path(CONFIG_FILE).exists(),
    reason=f"Credentials config file not found: '{CONFIG_FILE}'",
)
class TestRealCallsLoginNeeded:
    def test_login_by_oauth_ok(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"], login_by="oauth")
        mb.login()

        assert mb._logged_in

    def test_login_by_oauth_wrong_creds(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], "wrongpassword", login_by="oauth")
        with pytest.raises(AuthenticationError, match=r".*Login not accepted.*"):
            mb.login()
        assert mb._logged_in is False

    def test_login_by_oauth_already_logged_in(self, creds_config, caplog):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"], login_by="oauth")
        caplog.set_level(logging.DEBUG)
        mb.login()
        mb.login()  # should be faster, and emit debug message

        assert "already logged in" in caplog.text  # to verify we do take fast lane
        assert mb._logged_in

    def test_get_accounts_ok(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"])
        accounts = mb.get_accounts()

        assert isinstance(accounts, list)

    def test_get_loans_ok(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"])
        loans = mb.get_loans(d["accountid"])

        assert isinstance(loans, list)

    def test_get_reservations_ok(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"])
        res = mb.get_reservations(d["accountid"])

        assert isinstance(res, list)


@pytest.mark.real
class TestRealCalls:
    def test_get_item_info_ok(self, creds_config):
        url = "https://gent.bibliotheek.be/catalogus/jef-nys/de-koningin-van-onderland/strip/library-marc-vlacc_9920921"
        item = get_item_info(url)

        assert item.url == url
        assert item.title == "De koningin van Onderland"
        assert item.series_name == "De belevenissen van Jommeke"
        assert item.series_number == 3
        assert item.type == "Strip"
        assert (
            item.cover_url
            == "https://webservices.bibliotheek.be/index.php?func=cover&ISBN=9789462100534&VLACCnr=9920921&CDR=&EAN=&ISMN=&EBS=&coversize=medium"
        )
        assert item.isbn == "9789462100534"

    def test_get_item_info_nonexisting_url(self, creds_config):
        url = "https://gent.bibliotheek.be/catalogus/jef-nys/de-koningin-van-onderland/strip/does-not-exist"
        with pytest.raises(ItemAccessError, match=r".*Item detail page not found.*"):
            _item = get_item_info(url)
