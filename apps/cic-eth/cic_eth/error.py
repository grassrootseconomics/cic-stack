class TokenCountError(Exception):
    """Exception raised when wrong number of tokens have been given to a task
    """
    pass


class NotLocalTxError(Exception):
    """Exception raised when trying to access a tx not originated from a local task
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


class SignerError(Exception):
    """Exception raised when signer is unavailable or generates an error

    """
    pass


class EthError(Exception):
    """Exception raised when unspecified error from evm node is encountered

    """
    pass
