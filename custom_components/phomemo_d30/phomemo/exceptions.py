"""Exceptions for Phomemo printer driver."""


class PhomemoError(Exception):
    """Base exception for Phomemo driver."""


class RecoverableError(PhomemoError):
    """Recoverable error that can be retried."""


class FatalError(PhomemoError):
    """Fatal error that cannot be retried."""


class ConnectionError(RecoverableError):
    """Connection-related error."""
