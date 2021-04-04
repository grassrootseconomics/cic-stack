# standard imports
import logging

# external imports
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.tx import unpack
from chainqueue.query import get_tx
from chainqueue.state import set_cancel
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.tx import TxCache

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.nonce import Nonce
from cic_eth.admin.ctrl import (
        lock_send,
        unlock_send,
        lock_queue,
        unlock_queue,
        )
from cic_eth.queue.tx import queue_create
from cic_eth.eth.gas import create_check_gas_task

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task(bind=True)
def shift_nonce(self, chain_str, tx_hash_orig_hex, delta=1):
    """Shift all transactions with nonces higher than the offset by the provided position delta.

    Transactions who are replaced by transactions that move nonces will be marked as OVERRIDDEN.

    :param chainstr: Chain specification string representation
    :type chainstr: str
    :param tx_hash_orig_hex: Transaction hash to resolve to sender and nonce to use as shift offset
    :type tx_hash_orig_hex: str, 0x-hex
    :param delta: Amount
    """
    queue = None
    try:
        queue = self.request.delivery_info.get('routing_key')
    except AttributeError:
        pass

    chain_spec = ChainSpec.from_chain_str(chain_str)
    tx_brief = get_tx(tx_hash_orig_hex)
    tx_raw = bytes.fromhex(strip_0x(tx_brief['signed_tx'][2:]))
    tx = unpack(tx_raw, chain_spec)
    nonce = tx_brief['nonce']
    address = tx['from']

    logg.debug('shifting nonce {} position(s) for address {}, offset {}'.format(delta, address, nonce))

    lock_queue(None, chain_str, address)
    lock_send(None, chain_str, address)

    session = SessionBase.create_session()
    q = session.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.sender==address)
    q = q.filter(Otx.nonce>=nonce+delta)
    q = q.order_by(Otx.nonce.asc())
    otxs = q.all()

    tx_hashes = []
    txs = []
    for otx in otxs:
        tx_raw = bytes.fromhex(strip_0x(otx.signed_tx))
        tx_new = unpack(tx_raw, chain_spec)

        tx_previous_hash_hex = tx_new['hash']
        tx_previous_nonce = tx_new['nonce']

        del(tx_new['hash'])
        del(tx_new['hash_unsigned'])
        tx_new['nonce'] -= delta

        (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx_new, chain_str)
        logg.debug('tx {} -> {} nonce {} -> {}'.format(tx_previous_hash_hex, tx_hash_hex, tx_previous_nonce, tx_new['nonce']))

        otx = Otx(
            nonce=tx_new['nonce'],
            address=tx_new['from'],
            tx_hash=tx_hash_hex,
            signed_tx=tx_signed_raw_hex,
                )
        session.add(otx)
        session.commit()

        # TODO: cancel all first, then replace. Otherwise we risk two non-locked states for two different nonces.
        set_cancel(tx_previous_hash_hex, True)

        TxCache.clone(tx_previous_hash_hex, tx_hash_hex)

        tx_hashes.append(tx_hash_hex)
        txs.append(tx_signed_raw_hex)

    session.close()

    s = create_check_gas_and_send_task(
         txs, 
         chain_str,
         tx_new['from'],
         tx_new['gas'],
         tx_hashes, 
         queue,
        )

    s_unlock_send = celery.signature(
        'cic_eth.admin.ctrl.unlock_send',
        [
            chain_str,
            tx_new['from'],
            ],
        queue=queue,
        )
    s_unlock_direct = celery.signature(
        'cic_eth.admin.ctrl.unlock_queue',
        [
            chain_str,
            tx_new['from'],
            ],
        queue=queue,
        )
    s_unlocks = celery.group(s_unlock_send, s_unlock_direct)
    s.link(s_unlocks)
    s.apply_async()
