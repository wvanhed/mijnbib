# ruff: noqa: S301  # suspicious-pickle-usage
import configparser
import pickle
import sys
from pathlib import Path

import pytest

from mijnbib.mijnbibliotheek import MijnBibliotheek
from tests.save_testref import REF_ACCOUNTS, REF_ALLINFO, REF_HOLDS, REF_LOANS

# Read credentials from config file
CONFIG_FILE = "mijnbib.ini"
config = configparser.ConfigParser()
config.read(CONFIG_FILE)
try:
    username = config["DEFAULT"]["username"]
    password = config["DEFAULT"]["password"]
    account_id = config["DEFAULT"]["accountid"]
except KeyError as e:
    print(f"Create a file '{CONFIG_FILE}' that holds a section '[DEFAULT'] and the field {e}")
    sys.exit(-1)


@pytest.mark.skipif(
    not Path(REF_ACCOUNTS).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_accounts():
    with Path(REF_ACCOUNTS).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password)
    data = mb.get_accounts()
    assert data_expected == data


@pytest.mark.skipif(
    not Path(REF_LOANS).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_loans():
    with Path(REF_LOANS).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password)
    data = mb.get_loans(account_id)
    assert data_expected == data


@pytest.mark.skipif(
    not Path(REF_HOLDS).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_holds():
    with Path(REF_HOLDS).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password)
    data = mb.get_reservations(account_id)
    assert data_expected == data


@pytest.mark.skipif(
    not Path(REF_ALLINFO).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_allinfo():
    with Path(REF_ALLINFO).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password)
    data = mb.get_all_info()
    assert data_expected == data
