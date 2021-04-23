# standard imports
import datetime
import logging

# third-party imports
import celery
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.chain import ChainSpec

# local imports
from cic_eth.db.enum import LockEnum
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.lock import Lock
from cic_eth.task import (
        CriticalSQLAlchemyTask,
        )
from cic_eth.error import LockedError

celery_app = celery.current_app
logg = logging.getLogger()

@celery_app.task(base=CriticalSQLAlchemyTask)
def lock(chained_input, chain_spec_dict, address=ZERO_ADDRESS, flags=LockEnum.ALL, tx_hash=None):
    """Task wrapper to set arbitrary locks

    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param flags: Flags to set
    :type flags: number
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: New lock state for address
    :rtype: number
    """
    chain_str = '::'
    if chain_spec_dict != None:
        chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    r = Lock.set(chain_str, flags, address=address, tx_hash=tx_hash)
    logg.debug('Locked {} for {}, flag now {}'.format(flags, address, r))
    return chained_input


@celery_app.task(base=CriticalSQLAlchemyTask)
def unlock(chained_input, chain_spec_dict, address=ZERO_ADDRESS, flags=LockEnum.ALL):
    """Task wrapper to reset arbitrary locks

    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param flags: Flags to set
    :type flags: number
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: New lock state for address
    :rtype: number
    """
    chain_str = '::'
    if chain_spec_dict != None:
        chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    r = Lock.reset(chain_str, flags, address=address)
    logg.debug('Unlocked {} for {}, flag now {}'.format(flags, address, r))
    return chained_input


@celery_app.task(base=CriticalSQLAlchemyTask)
def lock_send(chained_input, chain_spec_dict, address=ZERO_ADDRESS, tx_hash=None):
    """Task wrapper to set send lock

    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: New lock state for address
    :rtype: number
    """
    chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    r = Lock.set(chain_str, LockEnum.SEND, address=address, tx_hash=tx_hash)
    logg.debug('Send locked for {}, flag now {}'.format(address, r))
    return chained_input


@celery_app.task(base=CriticalSQLAlchemyTask)
def unlock_send(chained_input, chain_spec_dict, address=ZERO_ADDRESS):
    """Task wrapper to reset send lock

    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: New lock state for address
    :rtype: number
    """
    chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    r = Lock.reset(chain_str, LockEnum.SEND, address=address)
    logg.debug('Send unlocked for {}, flag now {}'.format(address, r))
    return chained_input


@celery_app.task(base=CriticalSQLAlchemyTask)
def lock_queue(chained_input, chain_spec_dict, address=ZERO_ADDRESS, tx_hash=None):
    """Task wrapper to set queue direct lock

    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: New lock state for address
    :rtype: number
    """
    chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    r = Lock.set(chain_str, LockEnum.QUEUE, address=address, tx_hash=tx_hash)
    logg.debug('Queue direct locked for {}, flag now {}'.format(address, r))
    return chained_input


@celery_app.task(base=CriticalSQLAlchemyTask)
def unlock_queue(chained_input, chain_spec_dict, address=ZERO_ADDRESS):
    """Task wrapper to reset queue direct lock

    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: New lock state for address
    :rtype: number
    """
    chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    r = Lock.reset(chain_str, LockEnum.QUEUE, address=address)
    logg.debug('Queue direct unlocked for {}, flag now {}'.format(address, r))
    return chained_input


@celery_app.task(base=CriticalSQLAlchemyTask)
def check_lock(chained_input, chain_spec_dict, lock_flags, address=None):
    chain_str = '::'
    if chain_spec_dict != None:
        chain_str = str(ChainSpec.from_dict(chain_spec_dict))
    session = SessionBase.create_session()
    r = Lock.check(chain_str, lock_flags, address=ZERO_ADDRESS, session=session)
    if address != None:
        r |= Lock.check(chain_str, lock_flags, address=address, session=session)
    if r > 0:
        logg.debug('lock check {} has match {} for {}'.format(lock_flags, r, address))
        session.close()
        raise LockedError(r)
    session.flush()
    session.close()
    return chained_input
