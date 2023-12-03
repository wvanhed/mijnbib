"""
Defines the various errors that can be thrown be a plugin
"""


class PluginError(Exception):
    pass


class GeneralPluginError(PluginError):
    pass


class AccessError(PluginError):
    pass


class AuthenticationError(PluginError):
    """Exception raised when authentication has failed."""


class ExtendLoanError(PluginError):
    """Exception raised when extending loan(s) failed."""


class CanNotConnectError(PluginError):
    """Exception raised when the source (usually a website) can not be reached.

    Attributes:
        url -- url that could not be reached
    """

    def __init__(self, url=""):
        self.url = url

    def __str__(self):
        return str(self.url)


class IncompatibleSourceError(PluginError):
    """Exception raised for any general errors in parsing the source.

    Attributes:
        msg  -- explanation of the error
        html_body -- html source that was used in parsing and caused error
    """

    def __init__(self, msg, html_body: str):
        self.msg = msg
        self.html_body = html_body

    def __str__(self):
        return str(self.msg)
