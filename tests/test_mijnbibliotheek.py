import io
from typing import BinaryIO

import pytest

from mijnbib import MijnBibliotheek
from mijnbib.plugin_errors import AuthenticationError


class FakeMechanizeBrowser:
    def __init__(self, form_response: str) -> None:
        self._form_response = form_response.encode("utf8")

    def __setitem__(self, key, value):
        pass

    def open(self, url) -> BinaryIO:
        return io.BytesIO(b"some response html")

    def select_form(self, *args, **kwargs):
        pass

    def submit(self, *args, **kwargs) -> BinaryIO:
        return io.BytesIO(self._form_response)


def test_login_ok():
    mb = MijnBibliotheek("user", "pwd", "city")
    mb._br = FakeMechanizeBrowser(form_response="Profiel")  # type: ignore
    mb.login()

    assert mb._logged_in


def test_login_fails():
    mb = MijnBibliotheek("user", "pwd", "city")
    mb._br = FakeMechanizeBrowser(form_response="whatever")  # type: ignore

    with pytest.raises(AuthenticationError, match=r".*Login not accepted.*"):
        mb.login()
    assert mb._logged_in is False


def test_login_fails_because_of_privacy():
    mb = MijnBibliotheek("user", "pwd", "city")
    mb._br = FakeMechanizeBrowser(form_response="privacyverklaring is gewijzigd")  # type: ignore

    with pytest.raises(
        AuthenticationError,
        match=r".*Login not accepted \(likely need to accept privacy statement again\).*",
    ):
        mb.login()
    assert mb._logged_in is False
