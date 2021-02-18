# standard imports
import logging
import time
import datetime

# third-party imports
import celery
from hexathon import strip_0x
from sqlalchemy import or_
from sqlalchemy import not_
from sqlalchemy import tuple_
from sqlalchemy import func

# local imports
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.otx import OtxStateLog
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.lock import Lock
from cic_eth.db import SessionBase
from cic_eth.db.enum import (
        StatusEnum,
        LockEnum,
        StatusBits,
        is_alive,
        dead,
        )
from cic_eth.eth.util import unpack_signed_raw_tx # TODO: should not be in same sub-path as package that imports queue.tx
from cic_eth.error import NotLocalTxError
from cic_eth.error import LockedError

celery_app = celery.current_app
#logg = celery_app.log.get_default_logger()
logg = logging.getLogger()


@celery_app.task()
def create(nonce, holder_address, tx_hash, signed_tx, chain_str, obsolete_predecessors=True):
    """Create a new transaction queue record.

    :param nonce: Transaction nonce
    :type nonce: int
    :param holder_address: Sender address
    :type holder_address: str, 0x-hex
    :param tx_hash: Transaction hash
    :type tx_hash: str, 0x-hex
    :param signed_tx: Signed raw transaction
    :type signed_tx: str, 0x-hex
    :param chain_str: Chain spec string representation to create transaction for
    :type chain_str: str
    :returns: transaction hash
    :rtype: str, 0x-hash
    """
    #session = SessionBase.create_session()
    #sqlalchemy.exc.TimeoutError
    session = SessionBase.bind_session()
    lock = Lock.check_aggregate(chain_str, LockEnum.QUEUE, holder_address, session=session) 
    if lock > 0:
        SessionBase.release_session(session)
        raise LockedError(lock)

    o = Otx.add(
            nonce=nonce,
            address=holder_address,
            tx_hash=tx_hash,
            signed_tx=signed_tx,
            session=session,
            )
    session.flush()

    if obsolete_predecessors:
        # TODO: obsolete previous txs from same holder with same nonce
        q = session.query(Otx)
        q = q.join(TxCache)
        q = q.filter(Otx.nonce==nonce)
        q = q.filter(TxCache.sender==holder_address)
        q = q.filter(Otx.tx_hash!=tx_hash)
        q = q.filter(Otx.status<=StatusEnum.SENT)

        for otx in q.all():
            logg.info('otx {} obsoleted by {}'.format(otx.tx_hash, tx_hash))
            otx.cancel(confirmed=False, session=session)

    session.commit()


    SessionBase.release_session(session)
    logg.debug('queue created nonce {} from {} hash {}'.format(nonce, holder_address, tx_hash))
    return tx_hash


# TODO: Replace set_* with single task for set status
@celery_app.task()
def set_sent_status(tx_hash, fail=False):
    """Used to set the status after a send attempt

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :param fail: if True, will set a SENDFAIL status, otherwise a SENT status. (Default: False)
    :type fail: boolean
    :raises NotLocalTxError: If transaction not found in queue.
    :returns: True if tx is known, False otherwise
    :rtype: boolean
    """
    session = SessionBase.bind_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        logg.warning('not local tx, skipping {}'.format(tx_hash))
        session.close()
        return False

    if fail:
        o.sendfail(session=session)
    else:
        o.sent(session=session)

    session.commit()

    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def set_final_status(tx_hash, block=None, fail=False):
    """Used to set the status of an incoming transaction result. 

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :param block: Block number if final status represents a confirmation on the network
    :type block: number
    :param fail: if True, will set a SUCCESS status, otherwise a REVERTED status. (Default: False)
    :type fail: boolean
    :raises NotLocalTxError: If transaction not found in queue.
    """
    session = SessionBase.bind_session()

    q = session.query(
            Otx.nonce.label('nonce'),
            TxCache.sender.label('sender'),
            Otx.id.label('otxid'),
            )
    q = q.join(TxCache)
    q = q.filter(Otx.tx_hash==tx_hash)
    o = q.first()

    if o == None:
        SessionBase.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    nonce = o.nonce
    sender = o.sender
    otxid = o.otxid

    q = session.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hash)
    o = q.first()

    if fail:
        o.minefail(block, session=session)
    else:
        o.success(block, session=session)

    q = session.query(Otx)
    q = q.join(TxCache)
    q = q.filter(Otx.nonce==nonce)
    q = q.filter(TxCache.sender==sender)
    q = q.filter(Otx.tx_hash!=tx_hash)

    for otwo in q.all():
        otwo.cancel(True, session=session)

    session.commit()

    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def set_cancel(tx_hash, manual=False):
    """Used to set the status when a transaction is cancelled.

    Will set the state to CANCELLED or OVERRIDDEN

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :param manual: If set, status will be OVERRIDDEN. Otherwise CANCELLED.
    :type manual: boolean
    :raises NotLocalTxError: If transaction not found in queue.
    """

    session = SessionBase.create_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        session.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    if manual:
        o.override(session=session)
    else:
        o.cancel(session=session)

    session.commit()

    session.release_session(session)

    return tx_hash


@celery_app.task()
def set_rejected(tx_hash):
    """Used to set the status when the node rejects sending a transaction to network

    Will set the state to REJECTED

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    """

    session = SessionBase.bind_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        SessionBase.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    o.reject(session=session)
    session.commit()
    
    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def set_fubar(tx_hash):
    """Used to set the status when an unexpected error occurs.

    Will set the state to FUBAR

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    """

    session = SessionBase.bind_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        SessionBase.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    o.fubar(session=session)
    session.commit()

    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def set_manual(tx_hash):
    """Used to set the status when queue is manually changed

    Will set the state to MANUAL

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    """

    session = SessionBase.bind_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        SessionBase.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    o.manual(session=session)
    session.commit()

    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def set_ready(tx_hash):
    """Used to mark a transaction as ready to be sent to network

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    """
    session = SessionBase.bind_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        SessionBase.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    if o.status & StatusBits.GAS_ISSUES or o.status == StatusEnum.PENDING:
        o.readysend(session=session)
    else:
        o.retry(session=session)

    session.commit()

    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def set_waitforgas(tx_hash):
    """Used to set the status when a transaction must be deferred due to gas refill

    Will set the state to WAITFORGAS

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    """
    session = SessionBase.bind_session()

    o = session.query(Otx).filter(Otx.tx_hash==tx_hash).first()
    if o == None:
        SessionBase.release_session(session)
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    session.flush()

    o.waitforgas(session=session)
    session.commit()
    
    SessionBase.release_session(session)

    return tx_hash


@celery_app.task()
def get_state_log(tx_hash):

    logs = []
    
    session = SessionBase.bind_session()

    q = session.query(OtxStateLog)
    q = q.join(Otx)
    q = q.filter(Otx.tx_hash==tx_hash)
    q = q.order_by(OtxStateLog.date.asc())

    for l in q.all():
        logs.append((l.date, l.status,))

    SessionBase.release_session(session)

    return logs


@celery_app.task()
def get_tx_cache(tx_hash):
    """Returns an aggregate dictionary of outgoing transaction data and metadata

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    :returns: Transaction data
    :rtype: dict
    """
    session = SessionBase.bind_session()

    q = session.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hash)
    otx = q.first()

    if otx == None:
        SessionBase.release_session(session)
        raise NotLocalTxError(tx_hash)

    session.flush()

    q = session.query(TxCache)
    q = q.filter(TxCache.otx_id==otx.id)
    txc = q.first()

    SessionBase.release_session(session)

    tx = {
        'tx_hash': otx.tx_hash,
        'signed_tx': otx.signed_tx,
        'nonce': otx.nonce,
        'status': StatusEnum(otx.status).name,
        'status_code': otx.status,
        'source_token': txc.source_token_address,
        'destination_token': txc.destination_token_address,
        'block_number': txc.block_number,
        'tx_index': txc.tx_index,
        'sender': txc.sender,
        'recipient': txc.recipient,
        'from_value': int(txc.from_value),
        'to_value': int(txc.to_value),
        'date_created': txc.date_created,
        'date_updated': txc.date_updated,
        'date_checked': txc.date_checked,
            }

    return tx


@celery_app.task()
def get_lock(address=None):
    """Retrieve all active locks

    If address is set, the query will look up the lock for the specified address only. A list of zero or one elements is returned, depending on whether a lock is set or not.

    :param address: Get lock for only the specified address
    :type address: str, 0x-hex
    :returns: List of locks
    :rtype: list of dicts
    """
    session = SessionBase.bind_session()

    q = session.query(
            Lock.date_created,
            Lock.address,
            Lock.flags,
            Otx.tx_hash,
            )
    q = q.join(Otx, isouter=True)
    if address != None:
        q = q.filter(Lock.address==address)
    else:
        q = q.order_by(Lock.date_created.asc())
   
    locks = []
    for lock in q.all():
        o = {
            'date': lock[0],
            'address': lock[1],
            'tx_hash': lock[3],
            'flags': lock[2],
            }
        locks.append(o)

    SessionBase.release_session(session)

    return locks


@celery_app.task()
def get_tx(tx_hash):
    """Retrieve a transaction queue record by transaction hash

    :param tx_hash: Transaction hash of record to modify
    :type tx_hash: str, 0x-hex
    :raises NotLocalTxError: If transaction not found in queue.
    :returns: nonce, address and signed_tx (raw signed transaction)
    :rtype: dict
    """
    session = SessionBase.bind_session()

    q = session.query(Otx)
    q = q.filter(Otx.tx_hash==tx_hash)
    tx = q.first()

    SessionBase.release_session(session)

    if tx == None:
        raise NotLocalTxError('queue does not contain tx hash {}'.format(tx_hash))

    o = {
        'otx_id': tx.id,
        'nonce': tx.nonce,
        'signed_tx': tx.signed_tx,
        'status': tx.status,
            }
    logg.debug('get tx {}'.format(o))

    return o


@celery_app.task()
def get_nonce_tx(nonce, sender, chain_id):
    """Retrieve all transactions for address with specified nonce

    :param nonce: Nonce
    :type nonce: number
    :param address: Ethereum address
    :type address: str, 0x-hex
    :returns: Transactions
    :rtype: dict, with transaction hash as key, signed raw transaction as value
    """
    session = SessionBase.bind_session()
    
    q = session.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.sender==sender)
    q = q.filter(Otx.nonce==nonce)
   
    txs = {}
    for r in q.all():
        tx_signed_bytes = bytes.fromhex(r.signed_tx[2:])
        tx = unpack_signed_raw_tx(tx_signed_bytes, chain_id)
        if sender == None or tx['from'] == sender:
            txs[r.tx_hash] = r.signed_tx

    SessionBase.release_session(session)

    return txs



# TODO: pass chain spec instead of chain id
def get_paused_txs(status=None, sender=None, chain_id=0):
    """Returns not finalized transactions that have been attempted sent without success.

    :param status: If set, will return transactions with this local queue status only
    :type status: cic_eth.db.enum.StatusEnum
    :param recipient: Recipient address to return transactions for
    :type recipient: str, 0x-hex
    :param chain_id: Numeric chain id to use to parse signed transaction data
    :type chain_id: number
    :raises ValueError: Status is finalized, sent or never attempted sent
    :returns: Transactions
    :rtype: dict, with transaction hash as key, signed raw transaction as value
    """
    session = SessionBase.bind_session()

    q = session.query(Otx)

    if status != None:
        #if status == StatusEnum.PENDING or status >= StatusEnum.SENT:
        if status == StatusEnum.PENDING or status & StatusBits.IN_NETWORK or not is_alive(status):
            SessionBase.release_session(session)
            raise ValueError('not a valid paused tx value: {}'.format(status))
        q = q.filter(Otx.status.op('&')(status.value)==status.value)
        q = q.join(TxCache)
    else:
        q = q.filter(Otx.status>StatusEnum.PENDING.value)
        q = q.filter(not_(Otx.status.op('&')(StatusBits.IN_NETWORK.value)>0))

    if sender != None:
        q = q.filter(TxCache.sender==sender)

    txs = {}

    for r in q.all():
        tx_signed_bytes = bytes.fromhex(r.signed_tx[2:])
        tx = unpack_signed_raw_tx(tx_signed_bytes, chain_id)
        if sender == None or tx['from'] == sender:
            #gas += tx['gas'] * tx['gasPrice']
            txs[r.tx_hash] = r.signed_tx

    SessionBase.release_session(session)

    return txs


def get_status_tx(status, before=None, exact=False, limit=0):
    """Retrieve transaction with a specific queue status.

    :param status: Status to match transactions with
    :type status: str
    :param before: If set, return only transactions older than the timestamp
    :type status: datetime.dateTime
    :param limit: Limit amount of returned transactions
    :type limit: number
    :returns: Transactions
    :rtype: list of cic_eth.db.models.otx.Otx
    """
    txs = {}

    session = SessionBase.bind_session()
    
    q = session.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.date_updated<before)
    if exact:
        q = q.filter(Otx.status==status.value)
    else:
        q = q.filter(Otx.status.op('&')(status.value)==status.value)
    i = 0
    for o in q.all():
        if limit > 0 and i == limit:
            break
        txs[o.tx_hash] = o.signed_tx
        i += 1

    SessionBase.release_session(session)
    
    return txs


# TODO: move query to model
def get_upcoming_tx(status=StatusEnum.READYSEND, recipient=None, before=None, chain_id=0):
    """Returns the next pending transaction, specifically the transaction with the lowest nonce, for every recipient that has pending transactions.

    Will omit addresses that have the LockEnum.SEND bit in Lock set.

    (TODO) Will not return any rows if LockEnum.SEND bit in Lock is set for zero address.

    :param status: Defines the status used to filter as upcoming.
    :type status: cic_eth.db.enum.StatusEnum
    :param recipient: Ethereum address of recipient to return transaction for
    :type recipient: str, 0x-hex
    :param before: Only return transactions if their modification date is older than the given timestamp
    :type before: datetime.datetime
    :param chain_id: Chain id to use to parse signed transaction data
    :type chain_id: number
    :raises ValueError: Status is finalized, sent or never attempted sent
    :returns: Transactions
    :rtype: dict, with transaction hash as key, signed raw transaction as value
    """
    session = SessionBase.bind_session()
    
    q_outer = session.query(
            TxCache.sender,
            func.min(Otx.nonce).label('nonce'),
            )
    q_outer = q_outer.join(TxCache)
    q_outer = q_outer.join(Lock, isouter=True)
    q_outer = q_outer.filter(or_(Lock.flags==None, Lock.flags.op('&')(LockEnum.SEND.value)==0))

    if not is_alive(status):
        SessionBase.release_session(session)
        raise ValueError('not a valid non-final tx value: {}'.format(status))
    if status == StatusEnum.PENDING:
        q_outer = q_outer.filter(Otx.status==status.value)
    else:
        q_outer = q_outer.filter(Otx.status.op('&')(status.value)==status.value)

    if recipient != None:
        q_outer = q_outer.filter(TxCache.recipient==recipient)

    q_outer = q_outer.group_by(TxCache.sender)

    txs = {}

    for r in q_outer.all():
        q = session.query(Otx)
        q = q.join(TxCache)
        q = q.filter(TxCache.sender==r.sender)
        q = q.filter(Otx.nonce==r.nonce)

        if before != None:
            q = q.filter(TxCache.date_checked<before)
       
        q = q.order_by(TxCache.date_created.desc())
        o = q.first()

        # TODO: audit; should this be possible if a row is found in the initial query? If not, at a minimum log error.
        if o == None:
            continue

        tx_signed_bytes = bytes.fromhex(o.signed_tx[2:])
        tx = unpack_signed_raw_tx(tx_signed_bytes, chain_id)
        txs[o.tx_hash] = o.signed_tx
        
        q = session.query(TxCache)
        q = q.filter(TxCache.otx_id==o.id)
        o = q.first()

        o.date_checked = datetime.datetime.now()
        session.add(o)
        session.commit()

    SessionBase.release_session(session)

    return txs


@celery_app.task()
def get_account_tx(address, as_sender=True, as_recipient=True, counterpart=None):
    """Returns all local queue transactions for a given Ethereum address

    :param address: Ethereum address
    :type address: str, 0x-hex
    :param as_sender: If False, will omit transactions where address is sender
    :type as_sender: bool
    :param as_sender: If False, will omit transactions where address is recipient
    :type as_sender: bool
    :param counterpart: Only return transactions where this Ethereum address is the other end of the transaction (not in use)
    :type counterpart: str, 0x-hex
    :raises ValueError: If address is set to be neither sender nor recipient
    :returns: Transactions 
    :rtype: dict, with transaction hash as key, signed raw transaction as value
    """
    if not as_sender and not as_recipient:
        raise ValueError('at least one of as_sender and as_recipient must be True')

    txs = {}

    session = SessionBase.bind_session()
    
    q = session.query(Otx)
    q = q.join(TxCache)
    if as_sender and as_recipient:
        q = q.filter(or_(TxCache.sender==address, TxCache.recipient==address))
    elif as_sender:
        q = q.filter(TxCache.sender==address)
    else:
        q = q.filter(TxCache.recipient==address)
    q = q.order_by(Otx.nonce.asc(), Otx.date_created.asc()) 

    results = q.all()
    for r in results:
        if txs.get(r.tx_hash) != None:
            logg.debug('tx {} already recorded'.format(r.tx_hash))
            continue
        txs[r.tx_hash] = r.signed_tx

    SessionBase.release_session(session)

    return txs

