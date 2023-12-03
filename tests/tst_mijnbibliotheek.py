import pickle
from pathlib import Path

import pytest

import test_config as test_config
from mijnbib.mijnbibliotheek import MijnBibliotheek
from tests.save_testref import REF_ACCOUNTS, REF_ALLINFO, REF_HOLDS, REF_LOANS

username = test_config.mijnbib_user.split("#")[0]
password = test_config.mijnbib_pass
account_id = test_config.mijnbib_user.split("#")[1]
city = test_config.city


@pytest.mark.skipif(
    not Path(REF_ACCOUNTS).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_accounts():
    with Path(REF_ACCOUNTS).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_accounts()
    assert data_expected == data


@pytest.mark.skipif(
    not Path(REF_LOANS).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_loans():
    with Path(REF_LOANS).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_loans(account_id)
    assert data_expected == data


@pytest.mark.skipif(
    not Path(REF_HOLDS).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_holds():
    with Path(REF_HOLDS).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_reservations(account_id)
    assert data_expected == data


@pytest.mark.skipif(
    not Path(REF_ALLINFO).exists(),
    reason="No ref file. Create using save_testref script",
)
def test_get_allinfo():
    with Path(REF_ALLINFO).open("rb") as f:
        data_expected = pickle.load(f)
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_all_info()
    assert data_expected == data
