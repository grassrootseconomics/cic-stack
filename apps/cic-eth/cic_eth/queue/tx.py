# standard imports
import logging
import time
import datetime

# external imports
import celery
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.otx import OtxStateLog
from chainqueue.db.models.tx import TxCache
from hexathon import strip_0x
from sqlalchemy import or_
from sqlalchemy import not_
from sqlalchemy import tuple_
from sqlalchemy import func
from chainlib.chain import ChainSpec
from chainlib.eth.tx import unpack
import chainqueue.sql.state
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        dead,
        )
from chainqueue.sql.tx import create
from chainqueue.error import NotLocalTxError
from chainqueue.db.enum import status_str

# local imports
from cic_eth.db.models.lock import Lock
from cic_eth.db import SessionBase
from cic_eth.db.enum import LockEnum
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.error import LockedError
from cic_eth.encode import tx_normalize

celery_app = celery.current_app
logg = logging.getLogger()


def queue_create(chain_spec, nonce, holder_address, tx_hash, signed_tx, session=None):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    signed_tx = tx_normalize.tx_hash(signed_tx)
    holder_address = tx_normalize.wallet_address(holder_address)
    session = SessionBase.bind_session(session)

    lock = Lock.check_aggregate(str(chain_spec), LockEnum.QUEUE, holder_address, session=session) 
    if lock > 0:
        SessionBase.release_session(session)
        raise LockedError(lock)

    tx_hash = create(chain_spec, nonce, holder_address, tx_hash, signed_tx, chain_spec, session=session)
   
    SessionBase.release_session(session)

    return tx_hash


def register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=None, session=None):
    """Signs the provided transaction, and adds it to the transaction queue cache (with status PENDING).

    :param tx: Standard ethereum transaction data
    :type tx: dict
    :param chain_spec: Chain spec of transaction to add to queue
    :type chain_spec: chainlib.chain.ChainSpec
    :param queue: Task queue
    :type queue: str
    :param cache_task: Cache task to call with signed transaction. If None, no task will be called.
    :type cache_task: str
    :raises: sqlalchemy.exc.DatabaseError
    :returns: Tuple; Transaction hash, signed raw transaction data
    :rtype: tuple
    """
    tx_hash_hex = tx_normalize.tx_hash(tx_hash_hex)
    tx_signed_raw_hex = tx_normalize.tx_hash(tx_signed_raw_hex)
    logg.debug('adding queue tx {}:{} -> {}'.format(chain_spec, tx_hash_hex, tx_signed_raw_hex))
    tx_signed_raw = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw, chain_spec)

    tx_hash = queue_create(
        chain_spec,
        tx['nonce'],
        tx['from'],
        tx_hash_hex,
        tx_signed_raw_hex,
        session=session,
    )        

    if cache_task != None:
        logg.debug('adding cache task {} tx {}'.format(cache_task, tx_hash_hex))
        s_cache = celery.signature(
                cache_task,
                [
                    tx_hash_hex,
                    tx_signed_raw_hex,
                    chain_spec.asdict(),
                    ],
                queue=queue,
                )
        s_cache.apply_async()


