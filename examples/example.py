import logging
import pprint
from dataclasses import asdict

from mijnbib import MijnBibliotheek

logging.basicConfig(format="%(levelname)s %(message)s")
logging.getLogger().setLevel(logging.DEBUG)
pp = pprint.PrettyPrinter()

# Change these values !!!
city = "gent"
username = "johndoe"
password = "password"
account_id = "123456"

print("\nFetching accounts...")
mb = MijnBibliotheek(username, password, city)
accounts = mb.get_accounts()
pp.pprint([asdict(acc) for acc in accounts])

print("\nFetching loans...")
mb = MijnBibliotheek(username, password, city)
loans = mb.get_loans(account_id)
pp.pprint([asdict(loan) for loan in loans])

print("\nFetching reservations...")
mb = MijnBibliotheek(username, password, city)
reservations = mb.get_reservations(account_id)
pp.pprint([asdict(res) for res in reservations])

print("\nFetching all info...")
mb = MijnBibliotheek(username, password, city)
info = mb.get_all_info(all_as_dicts=True)
pp.pprint(info)

print("\nExtendable loans are:")
extendable_loans = []
for _key, acc in info.items():
    extendable_loans.extend([loan for loan in acc["loans"] if loan["extendable"]])
pp.pprint(extendable_loans)

# print("Extending loan...")
# mb = MijnBibliotheek(username, password, city)
# success, details = mb.extend_loans(
#     "<paste extend_url here>", # adapt this
#     False,  # set tot True, to actually extend a loan
# )
# pp.pprint(f"Extending loans success = {success}")
# pp.pprint(details)
