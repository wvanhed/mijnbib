from __future__ import annotations


class MijnbibError(Exception):
    """Base exception."""


# *** client-side errors ***


class AuthenticationError(MijnbibError):
    """Raised when authentication has failed.

    Args:
        msg          Descriptive message of the error
        html_body    Optional. Html body of the response involved, for diagnostics
        status_code  Optional. HTTP status code of the response involved
        url          Optional. Final (post-redirect) URL of the response involved
    """

    def __init__(
        self,
        msg,
        html_body: str | None = None,
        status_code: int | None = None,
        url: str | None = None,
    ):
        super().__init__(msg)
        self.html_body = html_body
        self.status_code = status_code
        self.url = url


class UnexpectedLoginRedirectError(AuthenticationError):
    """Raised when the login page did not redirect into the expected OAuth flow.

    This means the initial GET to the login page never received the
    `oauth_token`-carrying redirect it normally does, so no real credential
    check could even take place. In practice this has been observed when
    requests originate from cloud/datacenter IP ranges - i.e. it is much more
    likely to indicate bot/IP-based blocking by the site than a wrong
    username/password. It's still a subclass of `AuthenticationError` so
    existing `except AuthenticationError` handling keeps working.
    """


class ItemAccessError(MijnbibError):
    """Raised when an item (loan, reservation) could not be accessed.

    This is likely a client-side error, but in rare cases might have a
    server-side cause.
    """


# *** server-side errors ***


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
