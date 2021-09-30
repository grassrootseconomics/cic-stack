# standard imports
import datetime

# external imports
import celery
from chainlib.chain import ChainSpec
import chainqueue.sql.query
from chainlib.eth.tx import unpack
from chainqueue.db.enum import (
        StatusEnum,
        is_alive,
        )
from sqlalchemy import func
from sqlalchemy import or_
from chainqueue.db.models.tx import TxCache
from chainqueue.db.models.otx import Otx

# local imports
from cic_eth.db.enum import LockEnum
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.db.models.lock import Lock
from cic_eth.db.models.base import SessionBase
from cic_eth.encode import (
        tx_normalize,
        unpack_normal,
        )

celery_app = celery.current_app


@celery_app.task(base=CriticalSQLAlchemyTask)
def get_tx_cache(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return get_tx_cache_local(chain_spec, tx_hash)


def get_tx_cache_local(chain_spec, tx_hash, session=None):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    session = SessionBase.bind_session(session)
    r = chainqueue.sql.query.get_tx_cache(chain_spec, tx_hash, session=session)
    SessionBase.release_session(session)
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def get_tx(chain_spec_dict, tx_hash):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return get_tx_local(chain_spec, tx_hash)


def get_tx_local(chain_spec, tx_hash, session=None):
    tx_hash = tx_normalize.tx_hash(tx_hash)
    session = SessionBase.bind_session(session)
    r =  chainqueue.sql.query.get_tx(chain_spec, tx_hash, session=session)
    SessionBase.release_session(session)
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def get_account_tx(chain_spec_dict, address, as_sender=True, as_recipient=True, counterpart=None):
    address = tx_normalize.wallet_address(address)
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return get_account_tx_local(chain_spec, address, as_sender=as_sender, as_recipient=as_recipient, counterpart=counterpart)


def get_account_tx_local(chain_spec, address, as_sender=True, as_recipient=True, counterpart=None, session=None):
    address = tx_normalize.wallet_address(address)
    session = SessionBase.bind_session(session)
    r = chainqueue.sql.query.get_account_tx(chain_spec, address, as_sender=True, as_recipient=True, counterpart=None, session=session)
    SessionBase.release_session(session)
    return r


@celery_app.task(base=CriticalSQLAlchemyTask)
def get_upcoming_tx_nolock(chain_spec_dict, status=StatusEnum.READYSEND, not_status=None, recipient=None, before=None, limit=0):
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    return get_upcoming_tx_nolock_local(chain_spec, status=status, not_status=not_status, recipient=recipient, before=before, limit=limit)


def get_upcoming_tx_nolock_local(chain_spec, status=StatusEnum.READYSEND, not_status=None, recipient=None, before=None, limit=0, session=None):
    recipient = tx_normalize.wallet_address(recipient)
    session = SessionBase.create_session()
    r = chainqueue.sql.query.get_upcoming_tx(chain_spec, status, not_status=not_status, recipient=recipient, before=before, limit=limit, session=session, decoder=unpack_normal)
    session.close()
    return r


def get_status_tx(chain_spec, status, not_status=None, before=None, exact=False, limit=0, session=None):
    return chainqueue.sql.query.get_status_tx_cache(chain_spec, status, not_status=not_status, before=before, exact=exact, limit=limit, session=session, decoder=unpack_normal)


def get_paused_tx(chain_spec, status=None, sender=None, session=None, decoder=None):
    sender = tx_normalize.wallet_address(sender)
    return chainqueue.sql.query.get_paused_tx_cache(chain_spec, status=status, sender=sender, session=session, decoder=unpack_normal)


def get_nonce_tx(chain_spec, nonce, sender):
    sender = tx_normalize.wallet_address(sender)
    return get_nonce_tx_local(chain_spec, nonce, sender)


def get_nonce_tx_local(chain_spec, nonce, sender, session=None):
    sender = tx_normalize.wallet_address(sender)
    return chainqueue.sql.query.get_nonce_tx_cache(chain_spec, nonce, sender, decoder=unpack_normal, session=session)


def get_upcoming_tx(chain_spec, status=StatusEnum.READYSEND, not_status=None, recipient=None, before=None, limit=0, session=None):
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
    if recipient != None:
        recipient = tx_normalize.wallet_address(recipient)
    session = SessionBase.bind_session(session)
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
        q_outer = q_outer.filter(Otx.status.op('&')(status)==status)

    if not_status != None:
        q_outer = q_outer.filter(Otx.status.op('&')(not_status)==0)

    if recipient != None:
        q_outer = q_outer.filter(TxCache.recipient==recipient)

    q_outer = q_outer.group_by(TxCache.sender)

    txs = {}

    i = 0
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

        tx_signed_bytes = bytes.fromhex(o.signed_tx)
        tx = unpack(tx_signed_bytes, chain_spec)
        txs[o.tx_hash] = o.signed_tx
        
        q = session.query(TxCache)
        q = q.filter(TxCache.otx_id==o.id)
        o = q.first()

        o.date_checked = datetime.datetime.now()
        session.add(o)
        session.commit()

        i += 1
        if limit > 0 and limit == i:
            break

    SessionBase.release_session(session)

    return txs

