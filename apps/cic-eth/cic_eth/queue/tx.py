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
import chainqueue.state
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        dead,
        )
from chainqueue.error import NotLocalTxError
from chainqueue.db.enum import status_str

# local imports
from cic_eth.db.models.lock import Lock
from cic_eth.db import SessionBase
from cic_eth.db.enum import LockEnum
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.error import LockedError

celery_app = celery.current_app
logg = logging.getLogger()


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
    logg.debug('adding queue tx {}:{} -> {}'.format(chain_spec, tx_hash_hex, tx_signed_raw_hex))
    tx_signed_raw = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw, chain_id=chain_spec.chain_id())

    create(
        tx['nonce'],
        tx['from'],
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_spec,
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
