class MijnbibError(Exception):
    """Base exception."""


# *** client-side errors ***


class AuthenticationError(MijnbibError):
    """Raised when authentication has failed."""


class ItemAccessError(MijnbibError):
    """Raised when an item (loan, reservation) could not be accessed.

    This is likely a client-side error, but in rare cases might have a
    server-side cause.
    """


class InvalidExtendLoanURL(MijnbibError):
    """Raised when the extending loan(s) url is not considered valid."""


# *** server-side errors ***


class CanNotConnectError(MijnbibError):
    """Raised when a url can not be reached.

    Args:
        msg     Descriptive message of the error
        url     Url that could not be reached
    """

    def __init__(self, msg: str, url: str):
        super().__init__(msg)
        self.url = url


class IncompatibleSourceError(MijnbibError):
    """Raised for any general errors in parsing the source.

    Args:
        msg         Descriptive message of the error
        html_body   Html source that was used in parsing and caused error
    """

    def __init__(self, msg, html_body: str):
        super().__init__(msg)
        self.html_body = html_body


class ExtendLoanError(MijnbibError):
    """Raised when extending loan(s) failed for unclear reasons."""


class TemporarySiteError(MijnbibError):
    """Raised when the site reports a temporary error."""
