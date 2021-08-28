# standard imports
import os

# third-party imports
import pytest

# local imports
from cic_eth.db.models.lock import Lock
from cic_eth.db.enum import LockEnum
from cic_eth.error import LockedError
from cic_eth.queue.tx import queue_create
from cic_eth.encode import tx_normalize

def test_queue_lock(
    init_database,
    default_chain_spec,
        ):

    chain_str = str(default_chain_spec)

    address = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    tx_raw = '0x' + os.urandom(128).hex()
    address_normal = tx_normalize.wallet_address(address)
    tx_hash_normal = tx_normalize.tx_hash(tx_hash)

    Lock.set(chain_str, LockEnum.QUEUE)
    with pytest.raises(LockedError):
        queue_create(
                default_chain_spec,
                0,
                address, 
                tx_hash,
                tx_raw,
                )

    Lock.set(chain_str, LockEnum.QUEUE, address=address_normal)
    with pytest.raises(LockedError):
        queue_create(
                default_chain_spec,
                0,
                address, 
                tx_hash,
                tx_raw,
                )

    Lock.reset(chain_str, LockEnum.QUEUE)
    with pytest.raises(LockedError):
        queue_create(
                default_chain_spec,
                0,
                address, 
                tx_hash,
                tx_raw,
                )

    Lock.set(chain_str, LockEnum.QUEUE, address=address_normal, tx_hash=tx_hash_normal)
    with pytest.raises(LockedError):
        queue_create(
                default_chain_spec,
                0,
                address, 
                tx_hash,
                tx_raw,
                )
