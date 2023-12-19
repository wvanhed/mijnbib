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
    available_till: date | None = None
    request_on: date | None = None
    valid_till: date | None = None


@dataclass
class Account:
    library_name: str
    user: str
    id: str
    loans_count: int | None
    loans_url: str
    reservations_count: int | None
    reservations_url: str
    open_amounts: float
    open_amounts_url: str
