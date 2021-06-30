# standard import
from enum import IntEnum


class AccountStatus(IntEnum):
    PENDING = 1
    ACTIVE = 2
    LOCKED = 3
    RESET = 4
