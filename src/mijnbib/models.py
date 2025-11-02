"""Main dataclasses.

The properties of the classes reflect the available information in the
bibliotheek.be website, rather than a normalized data structure."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Loan:
    """A Loan object represents an item (e.g. book) with from and till loan date.

    There is no unique loan ID, since such an ID is not consistenly available in
    the bibliotheek.be web interface. The `id` property is a library-unique identifier
    of the actual item, and can be used to identify the same item across different
    (historic) loans.
    """

    title: str = ""
    loan_from: date | None = None
    loan_till: date | None = None
    author: str = ""
    type: str = ""  # item type, as given by the library, e.g. "Boek"
    extendable: bool | None = None
    extend_url: str = ""  # empty when `extendable` is False or None
    extend_id: str = ""  # can be used as input to extend multiple loans
    branchname: str = ""  # name of the library branch
    id: str = ""  # library-unique id for the item (not the loan!)
    url: str = ""
    cover_url: str = ""
    account_id: str = ""


@dataclass
class Reservation:
    """A Reservation object represent an item that has been reserved.

    There is no reservation ID, nor an ID for the item that is reserved,
    since this is not available in the bibliotheek.be web interface.
    The `url` property can be used to identify the reservation object.
    """

    title: str
    type: str
    url: str
    author: str
    location: str  # e.g. "Gent"
    available: bool
    available_till: date | None = None  # if available==True, indicates available untill
    request_on: date | None = None  # date of initial request for reservation
    valid_till: date | None = None  # request valid untill; once available, this becomes None


@dataclass
class Account:
    """An account represents a membership, i.e. a user linked to a library.

    Loans are always associated with a single account, via the account's `id`
    property.

    A user might have multiple accounts, in case he is linked to multiple
    libraries. The list of accounts that is visible to a logged in user consists
    of his own account(s) as well of any other associated accounts he has access
    to (e.g. children's accounts).
    """

    library_name: str  # e.g. "Dijk 92 - Bibliotheek Gent"
    user: str  # e.g. "John Doe"
    id: str  # e.g. "123456"
    loans_count: int | None  # None if number can not be determined
    loans_url: str
    reservations_count: int | None  # None if number can not be determined
    reservations_url: str
    open_amounts: float
    open_amounts_url: str
