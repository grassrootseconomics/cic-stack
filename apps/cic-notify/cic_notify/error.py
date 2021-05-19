class NotInitializedError(Exception):
    pass


class AlreadyInitializedError(Exception):
    pass


class PleaseCommitFirstError(Exception):
    """Raised when there exists uncommitted changes in the code while trying to build out the package."""
    pass


class NotificationSendError(Exception):
    """Raised when a notification failed to due to some error as per the service responsible for dispatching the notification."""
