# ruff: noqa: INP001  # this file is not part of package
"""This example shows how to extend the Loan object with extra details.

It uses get_item_info() to retrieve extra details for each loan item.

Change username and password in the main() function, then run using, for example:
    uv run python ./examples/loans_extras.py
"""

from __future__ import annotations

import pprint as pp
from dataclasses import asdict, dataclass

from mijnbib import Loan, MijnBibliotheek, get_item_info


@dataclass
class LoanExtra(Loan):
    """An extension of the Loan object with extra properties.

    These extra properties are only available on the detailed item page,
    not on the loans overview page.
    """

    series_name: str = ""  # e.g. "Suske en Wiske"
    series_number: int | None = None  # e.g. 3 for "#3" in the series
    isbn: str = ""  # e.g. "9780836221367"


def get_loans_extra(mb: MijnBibliotheek, account_id: str) -> list[LoanExtra]:
    """Return list of loans augmented with extra details.

    This requires visiting the detailed loans page for each loan of the
    account, which makes it considerably slower than `get_loans()`.
    """
    loans = mb.get_loans(account_id)

    loans_extras = []
    for loan in loans:
        print(".", end="", flush=True)
        loans_extra = LoanExtra(**asdict(loan))
        loans_extras.append(loans_extra)

        if not loan.url:
            continue

        item = get_item_info(loan.url)
        loans_extra.series_name = item.series_name
        loans_extra.series_number = item.series_number
        loans_extra.isbn = item.isbn
    print()
    return loans_extras


def main():
    # Change the following values to match your situation
    username = "johndoe"
    password = "password"  # noqa: S105

    mb = MijnBibliotheek(username, password)

    print("Retrieving accounts...")
    accounts = mb.get_accounts()

    accounts_with_loans = [a for a in accounts if a.loans_count]
    if accounts_with_loans:
        account = accounts_with_loans[0]
        print(f"Retrieving loans and extra details for account {account.id}...")
        result = get_loans_extra(mb, account.id)
        pp.pprint(result)
    else:
        print("No account with loans found.")


if __name__ == "__main__":
    main()
