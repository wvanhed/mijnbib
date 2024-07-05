import configparser
import io
import logging
from pathlib import Path
from typing import BinaryIO

import pytest

from mijnbib import MijnBibliotheek
from mijnbib.errors import AuthenticationError
from mijnbib.login_handlers import LoginByForm, LoginByOAuth
from mijnbib.models import Account, Loan, Reservation

CONFIG_FILE = "mijnbib.ini"


@pytest.fixture()
def creds_config(scope="module"):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    yield dict(**config.defaults())


class X(str):
    pass


class FakeMechanizeBrowser:
    """Fake Browser for easier testing.

    Set the string to be returned upon form submission using `form_response`.
    Customize the string for faking (in)valid login responses.
    """

    def __init__(self, form_response: str) -> None:
        self._form_response = form_response.encode("utf8")
        # trick for nested prop, from https://stackoverflow.com/a/35190607/50899
        self._factory = X("_factory")
        self._factory.is_html = None  # can be whatever

    def __setitem__(self, key, value):
        pass

    def open(self, url, timeout=0) -> BinaryIO:
        return io.BytesIO(b"some response html")

    def select_form(self, *args, **kwargs):
        pass

    def submit(self, *args, **kwargs) -> BinaryIO:
        return io.BytesIO(self._form_response)


class TestLoginByOption:
    def test_login_by_options_default_is_by_form(self):
        mb = MijnBibliotheek("user", "pwd", "city")
        assert mb._login_handler_class == LoginByForm

    def test_login_by_options_by_form(self):
        mb = MijnBibliotheek("user", "pwd", "city", "form")
        assert mb._login_handler_class == LoginByForm

    def test_login_by_options_by_oauth(self):
        mb = MijnBibliotheek("user", "pwd", "city", "oauth")
        assert mb._login_handler_class == LoginByOAuth

    def test_login_by_options_invalid_option_raises_error(self):
        with pytest.raises(ValueError):
            MijnBibliotheek("user", "pwd", "city", login_by="foo")


class TestFakedLogins:
    def test_login_ok(self):
        mb = MijnBibliotheek("user", "pwd", "city")
        mb._br = FakeMechanizeBrowser(form_response="Profiel")  # type: ignore
        mb.login()

        assert mb._logged_in

    def test_login_fails(self):
        mb = MijnBibliotheek("user", "pwd", "city")
        mb._br = FakeMechanizeBrowser(form_response="whatever")  # type: ignore

        with pytest.raises(AuthenticationError, match=r".*Login not accepted.*"):
            mb.login()
        assert mb._logged_in is False

    def test_login_fails_because_of_privacy(self):
        mb = MijnBibliotheek("user", "pwd", "city")
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
        mb = MijnBibliotheek(d["username"], d["password"], d["city"], login_by="form")
        mb.login()

        assert mb._logged_in

    def test_login_by_form_ok_no_city(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"], login_by="form")
        mb.login()

        assert mb._logged_in

    def test_login_by_form_wrong_creds(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], "wrongpassword", d["city"], login_by="form")
        with pytest.raises(AuthenticationError, match=r".*Login not accepted.*"):
            mb.login()
        assert mb._logged_in is False

    def test_login_by_oauth_ok(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"], d["city"], login_by="oauth")
        mb.login()

        assert mb._logged_in

    def test_login_by_oauth_ok_no_city(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], d["password"], login_by="oauth")
        mb.login()

        assert mb._logged_in

    def test_login_by_oauth_wrong_creds(self, creds_config):
        d = creds_config
        mb = MijnBibliotheek(d["username"], "wrongpassword", d["city"], login_by="oauth")
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

    def test_accounts_page_parser_can_be_overridden(self):
        # Arrange
        acc = Account("libname", "user", "id", 1, "loans_url", 1, "res_url", 1, "oa_url")

        class MyCustomAccountsParser:
            def parse(self, _html, _base_url):
                return [acc]

        mb = MijnBibliotheek("user", "pwd")
        # Fake both (a) valid login, and (b) some reponse on fetching accounts page
        mb._br = FakeMechanizeBrowser(form_response="Profiel")  # type: ignore

        # Act
        mb._accounts_page_parser = MyCustomAccountsParser()  # type:ignore

        # Assert
        assert mb.get_accounts() == [acc]

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
