from __future__ import annotations

import configparser
import io
import logging
from pathlib import Path
from typing import BinaryIO

import pytest

from mijnbib import MijnBibliotheek
from mijnbib.errors import AuthenticationError, IncompatibleSourceError
from mijnbib.login_handlers import LoginByForm, LoginByOAuth
from mijnbib.models import Account, Loan, Reservation

CONFIG_FILE = "mijnbib.ini"


@pytest.fixture
def creds_config(scope="module"):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return dict(**config.defaults())


class X(str):
    pass


class FakeMechanizeBrowser:
    """Fake Browser for easier testing.

    Set the string to be returned upon form submission using `form_response`.
    Customize the string for faking (in)valid login responses.

    Set the string to be returned upon opening a URL using `open_responses`.
    If `open_responses` is None, the open method will return a dummy response.
    """

    def __init__(self, form_response: str, open_responses: dict | None = None) -> None:
        self._form_response = form_response.encode("utf8")
        self._open_responses = open_responses
        # trick for nested prop, from https://stackoverflow.com/a/35190607/50899
        self._factory = X("_factory")
        self._factory.is_html = None  # can be whatever

    def __setitem__(self, key, value):
        pass

    def open(self, url, timeout=0) -> BinaryIO:
        # print("Opening URL:", url)
        if isinstance(self._open_responses, dict) and url in self._open_responses:
            response = self._open_responses[url]
        else:
            response = b"some response html"
        return io.BytesIO(response)

    def select_form(self, *args, **kwargs):
        pass

    def submit(self, *args, **kwargs) -> BinaryIO:
        return io.BytesIO(self._form_response)


class TestLoginByOption:
    def test_login_by_options_default_is_by_form(self):
        mb = MijnBibliotheek("user", "pwd")
        assert mb._login_handler_class == LoginByForm

    def test_login_by_options_by_form(self):
        mb = MijnBibliotheek("user", "pwd", login_by="form")
        assert mb._login_handler_class == LoginByForm

    def test_login_by_options_by_oauth(self):
        mb = MijnBibliotheek("user", "pwd", login_by="oauth")
        assert mb._login_handler_class == LoginByOAuth

    def test_login_by_options_invalid_option_raises_error(self):
        with pytest.raises(
            ValueError, match=r".*login_by needs to be either 'oauth' or 'form'.*"
        ):
            MijnBibliotheek("user", "pwd", login_by="foo")


class TestFakedLogins:
    def test_login_ok(self):
        mb = MijnBibliotheek("user", "pwd")
        mb._br = FakeMechanizeBrowser(form_response="Profiel")  # type: ignore
        mb.login()

        assert mb._logged_in

    def test_login_fails(self):
        mb = MijnBibliotheek("user", "pwd")
        mb._br = FakeMechanizeBrowser(form_response="whatever")  # type: ignore

        with pytest.raises(AuthenticationError, match=r".*Login not accepted.*"):
            mb.login()
        assert mb._logged_in is False

    def test_login_fails_because_of_privacy(self):
        mb = MijnBibliotheek("user", "pwd")
        mb._br = FakeMechanizeBrowser(form_response="privacyverklaring is gewijzigd")  # type: ignore

        with pytest.raises(
            AuthenticationError,
            match=r".*Login not accepted \(likely need to accept privacy statement again\).*",
        ):
            mb.login()
        assert mb._logged_in is False


@pytest.mark.skipif(
    not Path(CONFIG_FILE).exists(),
    reason=f"Credentials config file not found: '{CONFIG_FILE}'",
)
class TestRealLogins:
    def test_login_by_form_ok(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"], login_by="form")
        mb.login()

        assert mb._logged_in

    def test_login_by_form_wrong_creds(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], "wrongpassword", login_by="form")
        with pytest.raises(AuthenticationError, match=r".*Login not accepted.*"):
            mb.login()
        assert mb._logged_in is False

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


class TestCustomParser:
    def test_loans_page_parser_can_be_overridden(self):
        # Arrange
        class MyCustomLoanParser:
            def parse(self, _html, _base_url, _account_id):
                return [Loan("some title")]

        mb = MijnBibliotheek("user", "pwd")
        # Fake both (a) valid login, and (b) some reponse on fetching loans page
        mb._br = FakeMechanizeBrowser(form_response="Profiel")  # type: ignore

        # Act
        mb._loans_page_parser = MyCustomLoanParser()  # type:ignore

        # Assert
        assert mb.get_loans(account_id="whatever") == [Loan("some title")]

    def test_reservations_parser_can_be_overridden(self):
        # Arrange
        res = Reservation("title", "dvd", "some_url", "author", "brussels", True)

        class MyCustomReservationsParser:
            def parse(self, _html):
                return [res]

        mb = MijnBibliotheek("user", "pwd")
        # Fake both (a) valid login, and (b) some reponse on fetching reservations page
        mb._br = FakeMechanizeBrowser(form_response="Profiel")  # type: ignore

        # Act
        mb._reservations_parser = MyCustomReservationsParser()  # type:ignore

        # Assert
        assert mb.get_reservations(account_id="whatever") == [res]

    # def test_extendresponse_parser_can_be_overridden(self):
    # Not so easy to write test for


class TestGetAccounts:
    def test_get_accounts(self, caplog):
        mb = MijnBibliotheek("user", "pwd")
        mb._br = FakeMechanizeBrowser(  # type: ignore
            form_response="Profiel",  # needed for faking login
            open_responses={
                "https://bibliotheek.be/api/my-library/memberships": b"""
                    {
                    "Dijk92 - Bibliotheek Gent": [
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
                        "hasError": true,
                        "id": "111222",
                        "isBlocked": false,
                        "isExpired": false,
                        "libraryName": "Brussels",
                        "library": "https://bxl.bibliotheek.be",
                        "name": "Jane Smith"
                        }
                    ]
                    }
                """,
                "https://bibliotheek.be/api/my-library/123456/activities": b"""
                    {
                    "loanHistoryUrl": "/mijn-bibliotheek/lidmaatschappen/123456/leenhistoriek",
                    "numberOfHolds": 2,
                    "numberOfLoans": 5,
                    "openAmount": "3,20"
                    }
                """,
                "https://bibliotheek.be/api/my-library/111222/activities": b"""
                    {
                    "loanHistoryUrl": "/mijn-bibliotheek/lidmaatschappen/123456/leenhistoriek",
                    "numberOfHolds": 1,
                    "numberOfLoans": 1,
                    "openAmount": "5,00"
                    }
                """,
            },
        )  # type: ignore

        accounts = mb.get_accounts()

        # caplog.set_level(logging.WARNING)
        assert "Account 111222 reports error, skipping counts and amounts" in caplog.text

        assert accounts == [
            Account(
                library_name="Dijk92 - Bibliotheek Gent",
                id="123456",
                user="John Doe",
                open_amounts=3.20,
                loans_count=5,
                reservations_count=2,
                loans_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/uitleningen",
                reservations_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/reservaties",
                open_amounts_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/123456/te-betalen",
            ),
            # Note: 2nd account has `hasError` set to True, so some values are None
            Account(
                library_name="Brussels",
                id="111222",
                user="Jane Smith",
                open_amounts=0.00,  # 0 instead of 5.00,
                loans_count=None,  # must be None instead 1
                reservations_count=None,  # must be None instead 1
                loans_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/111222/uitleningen",
                reservations_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/111222/reservaties",
                open_amounts_url="https://bibliotheek.be/mijn-bibliotheek/lidmaatschappen/111222/te-betalen",
            ),
        ]

    def test_get_accounts_raises_incompatiblesource_error_on_invalid_json_for_memberships(
        self,
    ):
        mb = MijnBibliotheek("user", "pwd")
        mb._br = FakeMechanizeBrowser(  # type: ignore
            form_response="Profiel",  # needed for faking login
            open_responses={
                "https://bibliotheek.be/api/my-library/memberships": b"""
                    {
                    this is invalid json
                    }
                """
            },
        )  # type: ignore

        with pytest.raises(IncompatibleSourceError, match=r".*JSONDecodeError.*"):
            _accounts = mb.get_accounts()

    def test_get_accounts_raises_incompatiblesource_error_on_invalid_json_for_activity(self):
        mb = MijnBibliotheek("user", "pwd")
        mb._br = FakeMechanizeBrowser(  # type: ignore
            form_response="Profiel",  # needed for faking login
            open_responses={
                "https://bibliotheek.be/api/my-library/memberships": b"""
                    {
                    "Dijk92 - Bibliotheek Gent": [
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
                """,
                "https://bibliotheek.be/api/my-library/123456/activities": b"""
                    {
                    this is invalid json
                    }
                """,
            },
        )  # type: ignore

        with pytest.raises(IncompatibleSourceError, match=r".*JSONDecodeError.*"):
            _accounts = mb.get_accounts()
