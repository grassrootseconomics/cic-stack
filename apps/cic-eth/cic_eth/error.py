class TokenCountError(Exception):
    """Exception raised when wrong number of tokens have been given to a task
    """
    pass


class PermanentTxError(Exception):
    """Exception raised when encountering a permanent error when sending a tx.

    - wrong nonce
    - insufficient balance
    """
    pass


class TemporaryTxError(Exception):
    """Exception raised when encountering a permanent error when sending a tx.

    - blockchain node connection
    """
    pass

class OutOfGasError(Exception):
    """Exception raised when a transaction task must yield pending gas refill for an account

    """
    pass


class AlreadyFillingGasError(Exception):
    """Exception raised when additional gas refills are issued while one is still in progress

    """
    pass


class InitializationError(Exception):
    """Exception raised when initialization state is insufficient to run component

    """
    pass


class RoleMissingError(Exception):
    """Exception raised when web3 action attempted without an address with access to sign for it

    """
    pass


class IntegrityError(Exception):
    """Exception raised to signal irregularities with deduplication and ordering of tasks

    """
    pass


class LockedError(Exception):
    """Exception raised when attempt is made to execute action that is deactivated by lock

    """
    pass


class SeppukuError(Exception):
    """Exception base class for all errors that should cause system shutdown
    """
    def __init__(self, message, lockdown=False):
        self.message = message
        self.lockdown = lockdown


class SignerError(SeppukuError):
    """Exception raised when signer is unavailable or generates an error

    """
    pass


class RoleAgencyError(SeppukuError):
    """Exception raise when a role cannot perform its function. This is a critical exception
    """


class YouAreBrokeError(Exception):
    """Exception raised when a value transfer is attempted without access to sufficient funds
    """


class TrustError(Exception):
    """Exception raised when required trust proofs are missing for a request
    """
