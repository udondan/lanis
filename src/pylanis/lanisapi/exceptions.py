"""Exceptions raised by the Lanis library."""


class LanisError(Exception):
    """Base class of all errors raised by this library."""


class PageNotFoundError(LanisError):
    """Lanis answered with 404."""


class LoginPageRedirectError(LanisError):
    """Lanis answered with the login page, so the session is over."""


class NotAuthenticatedError(LanisError):
    """The client was used before ``authenticate()``."""


class AuthenticationError(LanisError):
    """The login flow did not produce a session."""


class WrongCredentialsError(AuthenticationError):
    """The username or password is wrong."""


class NoSchoolFoundError(AuthenticationError):
    """No school matches the given name and city."""


class AppNotAvailableError(LanisError):
    """The school does not offer the requested Lanis app."""


class CriticalElementWasNotFoundError(LanisError):
    """An HTML element the parser depends on is missing."""


class CryptionError(LanisError):
    """The encryption handshake with Lanis failed."""
