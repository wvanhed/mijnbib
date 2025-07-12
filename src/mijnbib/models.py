from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Loan:
    title: str = ""
    loan_from: date | None = None
    loan_till: date | None = None
    author: str = ""
    type: str = ""
    extendable: bool | None = None
    extend_url: str = ""  # empty when `extendable` is False or None
    extend_id: str = ""  # can be used as input to extend multiple loans
    branchname: str = ""
    id: str = ""
    url: str = ""
    cover_url: str = ""
    account_id: str = ""


@dataclass
class Reservation:
    title: str
    type: str
    url: str
    author: str
    location: str
    available: bool
    available_till: date | None = None  # if available==True, indicates available untill
    request_on: date | None = None  # date of initial request for reservation
    valid_till: date | None = None  # request valid untill; once available, this becomes None


@dataclass
class Account:
    """An account represents a membership, i.e. a user linked to a library.

    Loans are always associated with a single account, via the account `id`.

    A user might have multiple accounts, in case he is linked to multiple
    libraries. The list of accounts that is visible to a logged in user consists
    of his own account(s) as well of any other associated accounts he has access
    to (e.g. children's accounts).
    """

    library_name: str  # e.g. "Dijk 92 - Bibliotheek Gent"
    user: str  # e.g. "John Doe"
    id: str  # e.g. "123456"
    loans_count: int | None
    loans_url: str
    reservations_count: int | None
    reservations_url: str
    open_amounts: float
    open_amounts_url: str
