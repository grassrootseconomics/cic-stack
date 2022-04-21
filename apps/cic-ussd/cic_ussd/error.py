class VersionTooLowError(Exception):
    """Raised when the session version doesn't match latest version."""
    pass


class SessionNotFoundError(Exception):
    """Raised when queried session is not found in memory."""
    pass


class InvalidFileFormatError(Exception):
    """Raised when the file format is invalid."""
    pass


class AccountCreationDataNotFound(Exception):
    """Raised when account creation data matching a specific task uuid is not found in the redis cache"""
    pass


class MetadataNotFoundError(Exception):
    """Raised when metadata is expected but not available in cache."""
    pass


class UnsupportedMethodError(Exception):
    """Raised when the method passed to the make request function is unsupported."""
    pass


class CachedDataNotFoundError(Exception):
    """Raised when the method passed to the make request function is unsupported."""
    pass


class MetadataStoreError(Exception):
    """Raised when metadata storage fails"""
    pass


class SeppukuError(Exception):
    """Exception base class for all errors that should cause system shutdown"""
    pass


class InitializationError(Exception):
    """Exception raised when initialization state is insufficient to run component"""
    pass


class UnknownUssdRecipient(Exception):
    """Raised when a recipient of a transaction is not known to the ussd application."""


class MaxRetryReached(Exception):
    """Raised when the maximum number of retries defined for polling for the availability of a resource."""
