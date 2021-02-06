class VersionTooLowError(Exception):
    """Raised when the session version doesn't match latest version."""
    pass


class SessionNotFoundError(Exception):
    """Raised when queried session is not found in memory."""
    pass


class InvalidFileFormatError(OSError):
    """Raised when the file format is invalid."""
    pass


class ActionDataNotFoundError(OSError):
    """Raised when action data matching a specific task uuid is not found in the redis cache"""
    pass

