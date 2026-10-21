from __future__ import annotations

import sys
from typing import ClassVar

import pytest

from mijnbib import AuthenticationError, __version__, cli
from mijnbib.const import CONFIG_FILE


class FakeMijnBibliotheek:
    """Stands in for MijnBibliotheek so no http requests are made."""

    instances: ClassVar[list[FakeMijnBibliotheek]] = []
    login_error: Exception | None = None

    def __init__(self, username, password, city=None):
        self.username = username
        self.password = password
        self.city = city
        self.calls = []
        self._logged_in = False
        FakeMijnBibliotheek.instances.append(self)

    def login(self):
        self.calls.append(("login",))
        if FakeMijnBibliotheek.login_error is not None:
            raise FakeMijnBibliotheek.login_error
        self._logged_in = True

    def get_all_info(self):
        self.calls.append(("get_all_info",))
        return {"all": "info"}

    def get_accounts(self):
        self.calls.append(("get_accounts",))
        return ["account"]

    def get_loans(self, account_id):
        self.calls.append(("get_loans", account_id))
        return ["loan"]

    def get_reservations(self, account_id):
        self.calls.append(("get_reservations", account_id))
        return ["reservation"]


@pytest.fixture(autouse=True)
def fake_mb(monkeypatch, tmp_path):
    # Run in an empty dir, so a developer's own mijnbib.ini is never picked up
    monkeypatch.chdir(tmp_path)
    FakeMijnBibliotheek.instances = []
    FakeMijnBibliotheek.login_error = None
    monkeypatch.setattr(cli, "MijnBibliotheek", FakeMijnBibliotheek)
    return FakeMijnBibliotheek


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["mijnbib", *args])
    cli.main()


class TestCli:
    def test_version(self, monkeypatch, capsys):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, "--version")
        assert exc_info.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_subcommand_is_required(self, monkeypatch, capsys):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch)
        assert exc_info.value.code == 2
        assert "usage:" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "subcommand", ["all", "accounts", "loans", "reservations", "login"]
    )
    def test_missing_username_is_reported_on_stderr(self, monkeypatch, capsys, subcommand):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, subcommand, "-p", "pwd", "-a", "123")
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Parameter 'username' is required" in captured.err
        assert captured.out == ""

    def test_missing_password_is_reported(self, monkeypatch, capsys):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, "accounts", "-u", "john")
        assert exc_info.value.code == 2
        assert "Parameter 'password' is required" in capsys.readouterr().err

    @pytest.mark.parametrize("subcommand", ["loans", "reservations"])
    def test_missing_accountid_is_reported(self, monkeypatch, capsys, fake_mb, subcommand):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, subcommand, "-u", "john", "-p", "pwd")
        assert exc_info.value.code == 2
        assert "Parameter 'accountid' is required" in capsys.readouterr().err
        assert fake_mb.instances == []  # nothing was called

    @pytest.mark.parametrize("subcommand", ["all", "accounts", "login"])
    def test_accountid_not_required(self, monkeypatch, fake_mb, subcommand):
        run_cli(monkeypatch, subcommand, "-u", "john", "-p", "pwd")
        assert len(fake_mb.instances) == 1

    @pytest.mark.parametrize(
        ("subcommand", "expected_call", "expected_output"),
        [
            ("all", ("get_all_info",), "{'all': 'info'}"),
            ("accounts", ("get_accounts",), "['account']"),
            ("loans", ("get_loans", "123"), "['loan']"),
            ("reservations", ("get_reservations", "123"), "['reservation']"),
        ],
    )
    def test_subcommand_calls_api(
        self, monkeypatch, capsys, fake_mb, subcommand, expected_call, expected_output
    ):
        run_cli(monkeypatch, subcommand, "-u", "john", "-p", "pwd", "-c", "gent", "-a", "123")

        (mb,) = fake_mb.instances
        assert (mb.username, mb.password, mb.city) == ("john", "pwd", "gent")
        assert mb.calls == [expected_call]
        assert expected_output in capsys.readouterr().out

    def test_login_success(self, monkeypatch, capsys):
        run_cli(monkeypatch, "login", "-u", "john", "-p", "pwd")
        assert "Logged in: True" in capsys.readouterr().out

    def test_login_failure_is_reported(self, monkeypatch, capsys, fake_mb):
        fake_mb.login_error = AuthenticationError("wrong credentials")
        run_cli(monkeypatch, "login", "-u", "john", "-p", "pwd")
        out = capsys.readouterr().out
        assert "wrong credentials" in out
        assert "Logged in: False" in out

    def test_defaults_are_read_from_config_file(self, monkeypatch, tmp_path, fake_mb):
        (tmp_path / CONFIG_FILE).write_text(
            "[DEFAULT]\nusername = john\npassword = pwd\ncity = gent\naccountid = 456\n"
        )
        run_cli(monkeypatch, "loans")

        (mb,) = fake_mb.instances
        assert (mb.username, mb.password, mb.city) == ("john", "pwd", "gent")
        assert mb.calls == [("get_loans", "456")]

    def test_arguments_override_config_file(self, monkeypatch, tmp_path, fake_mb):
        (tmp_path / CONFIG_FILE).write_text(
            "[DEFAULT]\nusername = john\npassword = pwd\naccountid = 456\n"
        )
        run_cli(monkeypatch, "loans", "-u", "jane", "-a", "789")

        (mb,) = fake_mb.instances
        assert (mb.username, mb.password) == ("jane", "pwd")
        assert mb.calls == [("get_loans", "789")]
