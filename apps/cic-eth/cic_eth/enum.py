# standard imports
import enum


@enum.unique
class LockEnum(enum.IntEnum):
    """
    STICKY: When set, reset is not possible
    INIT: When set, startup is possible without second level sanity checks (e.g. gas gifter balance)
    START: When set, startup is not possible, regardless of state
    CREATE: Disable creation of accounts
    SEND: Disable sending to network
    QUEUE: Disable queueing new or modified transactions
    QUERY: Disable all queue state and transaction queries
    """
    STICKY=1
    INIT=2
    CREATE=4
    SEND=8
    QUEUE=16
    QUERY=32
    START=int(0x80000000)
    ALL=int(0x7ffffffe)
