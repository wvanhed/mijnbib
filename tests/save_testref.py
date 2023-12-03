"""This script allows to create a reference response set for mijnbibliotheek.

When ran, it create reference files, which can be used in the mijnbibliotheek 
tests as expected data. When the files do not exist, the idea is that the 
relevant tests will be skipped.
"""
import pickle
import sys
from pathlib import Path

from mijnbib.mijnbibliotheek import MijnBibliotheek

try:
    import test_config as test_config
except ModuleNotFoundError:
    print("First, create a file 'test_config.py' with the required data")
    sys.exit(0)

REF_ACCOUNTS = "test_ref_accounts.dat"
REF_LOANS = "test_ref_loans.dat"
REF_HOLDS = "test_ref_holds.dat"
REF_ALLINFO = "test_ref_allinfo.dat"

username = test_config.mijnbib_user.split("#")[0]
password = test_config.mijnbib_pass
account_id = test_config.mijnbib_user.split("#")[1]
city = test_config.city


def save_accounts():
    print(f"Fetching accounts; saving to `{REF_ACCOUNTS}`")
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_accounts()
    _save(data, REF_ACCOUNTS)


def save_loans():
    print(f"Fetching loans; saving to `{REF_LOANS}`")
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_loans(account_id)
    _save(data, REF_LOANS)


def save_holds():
    print(f"Fetching holds; saving to `{REF_HOLDS}`")
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_reservations(account_id)
    _save(data, REF_HOLDS)


def save_all_info():
    print(f"Fetching all info; saving to `{REF_ALLINFO}`")
    mb = MijnBibliotheek(username, password, city)
    data = mb.get_all_info()
    _save(data, REF_ALLINFO)


def _save(data, filename):
    with Path(filename).open("wb") as f:
        pickle.dump(data, f)


if __name__ == "__main__":
    save_accounts()
    save_loans()
    save_holds()
    save_all_info()
    print("Done. You can now run `pytest`.")
