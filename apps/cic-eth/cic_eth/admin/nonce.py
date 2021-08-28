# standard imports
import logging

# external imports
import celery
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.tx import (
        unpack,
        TxFactory,
        )
from chainlib.eth.gas import OverrideGasOracle
from chainqueue.sql.query import get_tx
from chainqueue.sql.state import set_cancel
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.tx import TxCache
from hexathon import (
        strip_0x,
        add_0x,
        uniform as hex_uniform,
        )
from potaahto.symbols import snake_and_camel

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
from cic_eth.task import BaseTask
from cic_eth.encode import tx_normalize

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task(bind=True, base=BaseTask)
def shift_nonce(self, chainspec_dict, tx_hash_orig_hex, delta=1):
    """Shift all transactions with nonces higher than the offset by the provided position delta.

    Transactions who are replaced by transactions that move nonces will be marked as OVERRIDDEN.

    :param chainstr: Chain specification string representation
    :type chainstr: str
    :param tx_hash_orig_hex: Transaction hash to resolve to sender and nonce to use as shift offset
    :type tx_hash_orig_hex: str, 0x-hex
    :param delta: Amount
    """
    chain_spec = ChainSpec.from_dict(chainspec_dict)
    rpc = RPCConnection.connect(chain_spec, 'default')
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')
    queue = None
    try:
        queue = self.request.delivery_info.get('routing_key')
    except AttributeError:
        pass

    session = BaseTask.session_func()
    tx_brief = get_tx(chain_spec, tx_hash_orig_hex, session=session)
    tx_raw = bytes.fromhex(strip_0x(tx_brief['signed_tx']))
    tx = unpack(tx_raw, chain_spec)
    nonce = tx_brief['nonce']
    address = tx['from']

    logg.debug('shifting nonce {} position(s) for address {}, offset {}, hash {}'.format(delta, address, nonce, tx['hash']))

    lock_queue(None, chain_spec.asdict(), address=address)
    lock_send(None, chain_spec.asdict(), address=address)

    set_cancel(chain_spec, strip_0x(tx['hash']), manual=True, session=session)

    query_address = tx_normalize.wallet_address(address)
    q = session.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.sender==query_address)
    q = q.filter(Otx.nonce>=nonce+delta)
    q = q.order_by(Otx.nonce.asc())
    otxs = q.all()

    tx_hashes = []
    txs = []
    gas_total = 0
    for otx in otxs:
        tx_raw = bytes.fromhex(strip_0x(otx.signed_tx))
        tx_new = unpack(tx_raw, chain_spec)
        tx_new = snake_and_camel(tx_new)

        tx_previous_hash_hex = tx_new['hash']
        tx_previous_nonce = tx_new['nonce']

        tx_new['gas_price'] += 1
        tx_new['gasPrice'] = tx_new['gas_price']
        tx_new['nonce'] -= delta
        gas_total += tx_new['gas_price'] * tx_new['gas']

        logg.debug('tx_new {}'.format(tx_new))
        logg.debug('gas running total {}'.format(gas_total))

        del(tx_new['hash'])
        del(tx_new['hash_unsigned'])
        del(tx_new['hashUnsigned'])

        gas_oracle = OverrideGasOracle(limit=tx_new['gas'], price=tx_new['gas_price'] + 1) # TODO: it should be possible to merely set this price here and if missing in the existing struct then fill it in (chainlib.eth.tx)
        c = TxFactory(chain_spec, signer=rpc_signer, gas_oracle=gas_oracle)
        (tx_hash_hex, tx_signed_raw_hex) = c.build_raw(tx_new)
        logg.debug('tx {} -> {} nonce {} -> {}'.format(tx_previous_hash_hex, tx_hash_hex, tx_previous_nonce, tx_new['nonce']))

        otx = Otx(
            tx_new['nonce'],
            tx_hash_hex,
            tx_signed_raw_hex,
            )
        session.add(otx)

        # TODO: cancel all first, then replace. Otherwise we risk two non-locked states for two different nonces.
        set_cancel(chain_spec, strip_0x(tx_previous_hash_hex), manual=True, session=session)

        TxCache.clone(tx_previous_hash_hex, tx_hash_hex, session=session)

        tx_hashes.append(tx_hash_hex)
        txs.append(tx_signed_raw_hex)
        session.commit()

    session.close()

    s = create_check_gas_task(
         txs, 
         chain_spec,
         #tx_new['from'],
         address,
         #gas=tx_new['gas'],
         gas=gas_total,
         tx_hashes_hex=tx_hashes, 
         queue=queue,
        )

    s_unlock_send = celery.signature(
        'cic_eth.admin.ctrl.unlock_send',
        [
            chain_spec.asdict(),
            address,
            #tx_new['from'],
            ],
        queue=queue,
        )
    s_unlock_direct = celery.signature(
        'cic_eth.admin.ctrl.unlock_queue',
        [
            chain_spec.asdict(),
            address,
            #tx_new['from'],
            ],
        queue=queue,
        )
    s_unlocks = celery.group(s_unlock_send, s_unlock_direct)
    s.link(s_unlocks)
    s.apply_async()
