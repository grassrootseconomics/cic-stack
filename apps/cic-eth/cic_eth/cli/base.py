# standard imports
import enum

# external imports
from chainlib.eth.cli import (
    argflag_std_read,
    argflag_std_write,
    argflag_std_base,
    Flag,
    )

class CICFlag(enum.IntEnum):
   
    # celery - nibble 1
    CELERY = 1

    # redis - nibble 2
    REDIS = 16
    REDIS_CALLBACK = 32

    # chain - nibble 3
    CHAIN = 256

    # sync - nibble 4
    SYNCER = 4096

    # server - nibble 5
    SERVER=65536

argflag_local_base = argflag_std_base | Flag.CHAIN_SPEC
argflag_local_task = CICFlag.CELERY
argflag_local_taskcallback = argflag_local_task | CICFlag.REDIS | CICFlag.REDIS_CALLBACK
argflag_local_chain = CICFlag.CHAIN
argflag_local_sync = CICFlag.SYNCER | CICFlag.CHAIN
argflag_local_server = CICFlag.SERVER | CICFlag.REDIS | CICFlag.REDIS_CALLBACK | CICFlag.CELERY | Flag.CHAIN_SPEC
