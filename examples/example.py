# ruff: noqa: INP001  # this file is not part of package
import logging
import pprint
from dataclasses import asdict

from mijnbib import MijnBibliotheek

logging.basicConfig(format="%(levelname)-7s %(message)s")
logging.getLogger().setLevel(logging.DEBUG)
pp = pprint.PrettyPrinter()

# Change the following values to match your situation
# city = "gent" # optional
username = "johndoe"
password = "password"  # noqa: S105
account_id = "123456"

print("\nFetching accounts...")
mb = MijnBibliotheek(username, password)
accounts = mb.get_accounts()
pp.pprint([asdict(acc) for acc in accounts])

print("\nFetching loans...")
mb = MijnBibliotheek(username, password)
loans = mb.get_loans(account_id)
pp.pprint([asdict(loan) for loan in loans])

print("\nFetching reservations...")
mb = MijnBibliotheek(username, password)
reservations = mb.get_reservations(account_id)
pp.pprint([asdict(res) for res in reservations])

print("\nFetching all info...")
mb = MijnBibliotheek(username, password)
info = mb.get_all_info(all_as_dicts=True)
pp.pprint(info)

print("\nExtendable loans are:")
extendable_loans = []
for _key, acc in info.items():
    # Note: .extend(...) call below is standard Python functionality for lists
    # It does NOT extend the loan(s)!
    extendable_loans.extend([loan for loan in acc["loans"] if loan["extendable"]])
pp.pprint(extendable_loans)

# print("Extending loan...")
# mb = MijnBibliotheek(username, password)
# success, details = mb.extend_loans(
#     "<paste extend_url here>", # adapt this
#     False,  # set tot True, to actually extend a loan
# )
# pp.pprint(f"Extending loans success = {success}")
# pp.pprint(details)
