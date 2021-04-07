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


class MetadataNotFoundError(OSError):
    """Raised when metadata is expected but not available in cache."""
    pass


class UnsupportedMethodError(OSError):
    """Raised when the method passed to the make request function is unsupported."""
    pass


class CachedDataNotFoundError(OSError):
    """Raised when the method passed to the make request function is unsupported."""
    pass


class MetadataStoreError(Exception):
    """Raised when metadata storage fails"""
    pass


