# standard imports
import os

# local imports
from cic_eth.db.models.lock import Lock
from cic_eth.db.enum import LockEnum


def test_lock(
        init_database,
        default_chain_spec,
        ):

    chain_str = str(default_chain_spec) 

    # Check matching flag for global (zero-address) lock
    a = 0xffffffffffffffff & LockEnum.CREATE
    r = Lock.set(chain_str, a)
    assert r == a
    assert Lock.check(chain_str, a) > 0

    # Check matching flag for address specific lock
    address = '0x' + os.urandom(20).hex()
    b = 0xffffffffffffffff & (LockEnum.QUEUE | LockEnum.SEND)
    Lock.set(chain_str, b, address=address)
    assert Lock.check(chain_str, b, address=address) == b
    assert Lock.check(chain_str, a, address=address) == 0
    assert Lock.check(chain_str, b & LockEnum.QUEUE, address=address) == LockEnum.QUEUE
    assert Lock.check(chain_str, b) == 0

    # Reset single flag
    r = Lock.reset(chain_str, LockEnum.QUEUE, address=address)
    assert r == LockEnum.SEND

    # Reset to 0
    r = Lock.reset(chain_str, LockEnum.SEND, address=address)
    assert r == 0
    
    # Row should be deleted when flags value reaches 0
    q = init_database.query(Lock)
    q = q.filter(Lock.address==address)
    assert q.first() == None



def test_lock_merge_check(
        init_database,
        default_chain_spec,
        ):

    chain_str = str(default_chain_spec) 

    foo_address = '0x' + os.urandom(20).hex()
    bar_address = '0x' + os.urandom(20).hex()

    Lock.set(chain_str, LockEnum.CREATE)
    assert Lock.check_aggregate(chain_str, LockEnum.CREATE, address=foo_address) > 0
    assert Lock.check_aggregate(chain_str, LockEnum.CREATE, address=bar_address) > 0


    Lock.set(chain_str, LockEnum.CREATE, address=foo_address)
    assert Lock.check_aggregate(chain_str, LockEnum.CREATE, address=foo_address) > 0
    assert Lock.check_aggregate(chain_str, LockEnum.CREATE, address=bar_address) > 0

    Lock.reset(chain_str, LockEnum.CREATE)
    assert Lock.check_aggregate(chain_str, LockEnum.CREATE, address=foo_address) > 0
    assert Lock.check_aggregate(chain_str, LockEnum.CREATE, address=bar_address) == 0
