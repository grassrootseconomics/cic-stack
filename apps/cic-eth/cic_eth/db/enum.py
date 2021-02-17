# standard imports
import enum


@enum.unique
class StatusBits(enum.IntEnum):
    """Individual bit flags that are combined to define the state and legacy of a queued transaction

    """
    QUEUED = 0x01 # transaction should be sent to network
    IN_NETWORK = 0x08 # transaction is in network
   
    DEFERRED = 0x10 # an attempt to send the transaction to network has failed
    GAS_ISSUES = 0x20 # transaction is pending sender account gas funding

    LOCAL_ERROR = 0x100 # errors that originate internally from the component
    NODE_ERROR = 0x200 # errors originating in the node (invalid RLP input...)
    NETWORK_ERROR = 0x400 # errors that originate from the network (REVERT)
    UNKNOWN_ERROR = 0x800 # unclassified errors (the should not occur)

    FINAL = 0x1000 # transaction processing has completed
    OBSOLETE = 0x2000 # transaction has been replaced by a different transaction with higher fee
    MANUAL = 0x8000 # transaction processing has been manually overridden


@enum.unique
class StatusEnum(enum.IntEnum):
    """

    - Inactive, not finalized. (<0)
        * PENDING: The initial state of a newly added transaction record. No action has been performed on this transaction yet.
        * SENDFAIL: The transaction was not received by the node.
        * RETRY: The transaction is queued for a new send attempt after previously failing.
        * READYSEND: The transaction is queued for its first send attempt
        * OBSOLETED: A new transaction with the same nonce and higher gas has been sent to network.
        * WAITFORGAS: The transaction is on hold pending gas funding.
    - Active state: (==0)
        * SENT: The transaction has been sent to the mempool.
    - Inactive, finalized. (>0)
        * FUBAR: Unknown error occurred and transaction is abandoned. Manual intervention needed.
        * CANCELLED: The transaction was sent, but was not mined and has disappered from the mempool. This usually follows a transaction being obsoleted.
        * OVERRIDDEN: Transaction has been manually overriden.
        * REJECTED: The transaction was rejected by the node.
        * REVERTED: The transaction was mined, but exception occurred during EVM execution. (Block number will be set)
        * SUCCESS: THe transaction was successfully mined. (Block number will be set)

    """
    PENDING = 0

    SENDFAIL = StatusBits.DEFERRED | StatusBits.LOCAL_ERROR
    RETRY = StatusBits.QUEUED | StatusBits.DEFERRED 
    READYSEND = StatusBits.QUEUED

    OBSOLETED = StatusBits.OBSOLETE | StatusBits.IN_NETWORK

    WAITFORGAS = StatusBits.GAS_ISSUES

    SENT = StatusBits.IN_NETWORK
    FUBAR = StatusBits.FINAL | StatusBits.UNKNOWN_ERROR
    CANCELLED = StatusBits.IN_NETWORK | StatusBits.FINAL | StatusBits.OBSOLETE
    OVERRIDDEN = StatusBits.FINAL | StatusBits.OBSOLETE | StatusBits.MANUAL

    REJECTED = StatusBits.NODE_ERROR | StatusBits.FINAL
    REVERTED = StatusBits.IN_NETWORK | StatusBits.FINAL | StatusBits.NETWORK_ERROR
    SUCCESS = StatusBits.IN_NETWORK | StatusBits.FINAL 


@enum.unique
class LockEnum(enum.IntEnum):
    """
    STICKY: When set, reset is not possible
    CREATE: Disable creation of accounts
    SEND: Disable sending to network
    QUEUE: Disable queueing new or modified transactions
    """
    STICKY=1
    CREATE=2
    SEND=4
    QUEUE=8
    QUERY=16
    ALL=int(0xfffffffffffffffe)


def status_str(v, bits_only=False):
    """Render a human-readable string describing the status

    If the bit field exactly matches a StatusEnum value, the StatusEnum label will be returned.

    If a StatusEnum cannot be matched, the string will be postfixed with "*", unless explicitly instructed to return bit field labels only.

    :param v: Status bit field
    :type v: number
    :param bits_only: Only render individual bit labels.
    :type bits_only: bool
    :returns: Status string
    :rtype: str
    """
    s = ''
    if not bits_only:
        try:
            s = StatusEnum(v).name
            return s
        except ValueError:
            pass

    for i in range(16):
        b = (1 << i)
        if (b & 0xffff) & v:
            n = StatusBits(b).name
            if len(s) > 0:
                s += ','
            s += n
    if not bits_only:
        s += '*'
    return s


def all_errors():
    """Bit mask of all error states

    :returns: Error flags
    :rtype: number
    """
    return StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR | StatusBits.NETWORK_ERROR | StatusBits.UNKNOWN_ERROR


def is_error_status(v):
    """Check if value is an error state

    :param v: Status bit field
    :type v: number
    :returns: True if error
    :rtype: bool
    """
    return bool(v & all_errors())


def dead():
    """Bit mask defining whether a transaction is still likely to be processed on the network.

    :returns: Bit mask
    :rtype: number
    """
    return StatusBits.FINAL | StatusBits.OBSOLETE


def is_alive(v):
    """Check if transaction is still likely to be processed on the network.

    The contingency of "likely" refers to the case a transaction has been obsoleted after sent to the network, but the network still confirms the obsoleted transaction. The return value of this method will not change as a result of this, BUT the state itself will (as the FINAL bit will be set).

    :returns: 
    """
    return bool(v & dead() == 0)
