import configparser
import io
from pathlib import Path
from typing import BinaryIO

import pytest

from mijnbib import MijnBibliotheek
from mijnbib.errors import AuthenticationError
from mijnbib.login_handlers import LoginByForm, LoginByOAuth

CONFIG_FILE = "mijnbib.ini"


@pytest.fixture()
def creds_config(scope="module"):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    yield dict(**config.defaults())


class FakeMechanizeBrowser:
    def __init__(self, form_response: str) -> None:
        self._form_response = form_response.encode("utf8")

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
