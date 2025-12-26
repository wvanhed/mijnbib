# ruff: noqa: F401
import importlib.metadata

try:
    # __package__ allows for the case where __name__ is "__main__"
    __version__ = importlib.metadata.version(__package__ or __name__)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"


# So user can do e.g.
#   from mijnbib import MijnBibliotheek, Loan
from .errors import (
    AuthenticationError,
    ExtendLoanError,
    IncompatibleSourceError,
    ItemAccessError,
    MijnbibError,
    TemporarySiteError,
)
from .mijnbibliotheek import MijnBibliotheek, get_item_info
from .models import Account, Loan, Reservation
