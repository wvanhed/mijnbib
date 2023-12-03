import logging
import pprint
from dataclasses import asdict

from mijnbib import MijnBibliotheek

logging.basicConfig(format="%(levelname)s %(message)s")
logging.getLogger().setLevel(logging.DEBUG)
pp = pprint.PrettyPrinter()

try:
    import test_config as test_config
except ModuleNotFoundError:
    print("First, create a file 'test_config.py' with the required data")
    exit(-1)

# Create a test_config file with the following variables
# Or assign directly here
city = test_config.city
username = test_config.mijnbib_user.split("#")[0]
password = test_config.mijnbib_pass
account_id = test_config.mijnbib_user.split("#")[1]

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
