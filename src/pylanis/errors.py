"""Exceptions raised by the pylanis SDK."""


class LanisError(Exception):
    """Base class for all pylanis errors."""


class ConfigurationError(LanisError, ValueError):
    """The credentials passed to Lanis are incomplete."""


class SessionExpiredError(LanisError):
    """The Lanis session expired. The client was reset; retry the call."""
