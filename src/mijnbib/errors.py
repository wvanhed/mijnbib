class PluginError(Exception):
    """Base exception."""


# *** client-side errors ***


class AuthenticationError(PluginError):
    """Raised when authentication has failed."""


class ItemAccessError(PluginError):
    """Raised when an item (loan, reservation) could not be accessed.

    This is likely a client-side error, but in rare cases might have a
    server-side cause.
    """


class InvalidExtendLoanURL(PluginError):
    """Raised when the extending loan(s) url is not considered valid."""


# *** server-side errors ***


class CanNotConnectError(PluginError):
    """Raised when a url can not be reached.

    Args:
        msg     Descriptive message of the error
        url     Url that could not be reached
    """

    def __init__(self, msg: str, url: str):
        super().__init__(msg)
        self.url = url


class IncompatibleSourceError(PluginError):
    """Raised for any general errors in parsing the source.

    Args:
        msg         Descriptive message of the error
        html_body   Html source that was used in parsing and caused error
    """

    def __init__(self, msg, html_body: str):
        super().__init__(msg)
        self.html_body = html_body


class ExtendLoanError(PluginError):
    """Raised when extending loan(s) failed for unclear reasons."""


class TemporarySiteError(PluginError):
    """Raised when the site reports a temporary error."""
