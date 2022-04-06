# standard imports
import logging

# external imports
import celery
from chainlib.chain import ChainSpec
from chainlib.error import JSONRPCException
from chainlib.eth.address import is_checksum_address
from chainlib.eth.error import NotFoundEthException
from chainlib.eth.tx import (
        transaction,
        receipt,
        raw,
        )
from chainlib.connection import RPCConnection
from chainlib.hash import keccak256_hex_to_hex
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainqueue.db.models.tx import Otx
from chainqueue.db.enum import StatusBits
from chainqueue.error import NotLocalTxError
from potaahto.symbols import snake_and_camel

# local imports
from cic_eth.db import SessionBase
from cic_eth.error import (
        PermanentTxError,
        TemporaryTxError,
        )
from cic_eth.eth.gas import create_check_gas_task
from cic_eth.admin.ctrl import lock_send
from cic_eth.task import (
        CriticalSQLAlchemyTask,
        CriticalWeb3Task,
        CriticalWeb3AndSignerTask,
        CriticalSQLAlchemyAndSignerTask,
        CriticalSQLAlchemyAndWeb3Task,
        )

celery_app = celery.current_app
logg = logging.getLogger()

MAX_NONCE_ATTEMPTS = 3


# TODO: chain chainable transactions that use hashes as inputs may be chained to this function to output signed txs instead.
@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def hashes_to_txs(self, tx_hashes):
    """Return a list of raw signed transactions from the local transaction queue corresponding to a list of transaction hashes.

    :param tx_hashes: Transaction hashes
    :type tx_hashes: list of str, 0x-hex
    :raises ValueError: Empty input list
    :returns: Signed raw transactions
    :rtype: list of str, 0x-hex
    """
    if len(tx_hashes) == 0:
        raise ValueError('no transaction to send')

    for i in range(len(tx_hashes)):
        tx_hashes[i] = strip_0x(tx_hashes[i])

    queue = self.request.delivery_info['routing_key']

    session = SessionBase.create_session()
    q = session.query(Otx.signed_tx)
    q = q.filter(Otx.tx_hash.in_(tx_hashes))
    tx_tuples = q.all()
    session.close()

    def __head(x):
        return x[0]

    txs = []
    for f in map(__head, tx_tuples):
        txs.append(f)

    return txs


# TODO: A lock should be introduced to ensure that the send status change and the transaction send is atomic.
@celery_app.task(bind=True, base=CriticalWeb3Task)
def send(self, txs, chain_spec_dict):
    """Send transactions to the network.

    If more than one transaction is passed to the task, it will spawn a new send task with the remaining transaction(s) after the first in the list has been processed.

    Updates the outgoing transaction queue entry to SENT on successful send.

    If a temporary error occurs, the queue entry is set to SENDFAIL.

    If a permanent error occurs due to invalid transaction data, queue entry value is set to REJECTED.

    Any other permanent error that isn't explicitly handled will get value FUBAR.

    :param txs: Signed raw transaction data
    :type txs: list of str, 0x-hex
    :param chain_str: Chain spec, string representation
    :type chain_str: str
    :raises TemporaryTxError: If unable to connect to node
    :raises PermanentTxError: If EVM execution fails immediately due to tx input, or if tx contents are invalid. 
    :return: transaction hash of sent transaction
    :rtype: str, 0x-hex
    """
    if len(txs) == 0:
        raise ValueError('no transaction to send')

    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    tx_hex = add_0x(txs[0])

    tx_hash_hex = add_0x(keccak256_hex_to_hex(tx_hex))

    logg.debug('send transaction {} -> {}'.format(tx_hash_hex, tx_hex))

    queue = self.request.delivery_info.get('routing_key')

    o = raw(tx_hex)
    err_state = False
    conn = RPCConnection.connect(chain_spec, 'default')
    try:
        conn.do(o)
    except JSONRPCException as e:
        logg.error('send to node failed! {}'.format(e))
        err_state = True

    r = None
    s_set_sent = celery.signature(
        'cic_eth.queue.state.set_sent',
        [
            chain_spec_dict,
            tx_hash_hex,
            err_state,
            ],
            queue=queue,
        )

    s_set_sent.apply_async()

    tx_tail = txs[1:]
    if len(tx_tail) > 0:
        s = celery.signature(
            'cic_eth.eth.tx.send',
            [
                tx_tail,
                chain_spec_dict,
            ],
            queue=queue,
                )
        s.apply_async()

    return tx_hash_hex



@celery_app.task(bind=True, throws=(NotFoundEthException,), base=CriticalWeb3Task)
def sync_tx(self, tx_hash_hex, chain_spec_dict):
    """Force update of network status of a single transaction

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    """

    queue = self.request.delivery_info.get('routing_key')

    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    conn = RPCConnection.connect(chain_spec, 'default')
    o = transaction(tx_hash_hex)
    tx = conn.do(o)

    rcpt = None
    try:
        o = receipt(tx_hash_hex)
        rcpt = conn.do(o)
    except NotFoundEthException as e:
        pass

    # TODO: apply receipt in tx object to validate and normalize input
    if rcpt != None:
        rcpt = snake_and_camel(rcpt)
        success = rcpt['status'] == 1
        logg.debug('sync tx {} mined block {} tx index {} success {}'.format(tx_hash_hex, rcpt['blockNumber'], rcpt['transactionIndex'], success))

        s = celery.signature(
            'cic_eth.queue.state.set_final',
            [
                chain_spec_dict,
                tx_hash_hex,
                rcpt['blockNumber'],
                rcpt['transactionIndex'],
                not success,
                ],
                queue=queue,
            )
    # TODO: it's not entirely clear how we can reliable determine that its in mempool without explicitly checking
    else:
        logg.debug('sync tx {} mempool'.format(tx_hash_hex))

        s = celery.signature(
            'cic_eth.queue.state.set_sent',
            [
                chain_spec_dict,
                tx_hash_hex,
                ],
                queue=queue,
            )

    s.apply_async()


#
#@celery_app.task(bind=True)
#def resume_tx(self, txpending_hash_hex, chain_str):
#    """Queue a suspended tranaction for (re)sending
#
#    :param txpending_hash_hex: Transaction hash
#    :type txpending_hash_hex: str, 0x-hex
#    :param chain_str: Chain spec, string representation
#    :type chain_str: str
#    :raises NotLocalTxError: Transaction does not exist in the local queue
#    :returns: Transaction hash
#    :rtype: str, 0x-hex
#    """
#
#    chain_spec = ChainSpec.from_chain_str(chain_str)
#
#    session = SessionBase.create_session()
#    q = session.query(Otx.signed_tx)
#    q = q.filter(Otx.tx_hash==txpending_hash_hex)
#    r = q.first()
#    session.close()
#    if r == None:
#        raise NotLocalTxError(txpending_hash_hex)
#
#    tx_signed_raw_hex = r[0]
#    tx_signed_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
#    tx = unpack(tx_signed_bytes, chain_spec)
#
#    queue = self.request.delivery_info['routing_key']
#
#    s = create_check_gas_and_send_task(
#            [tx_signed_raw_hex],
#            chain_str,
#            tx['from'],
#            tx['gasPrice'] * tx['gas'],
#            [txpending_hash_hex],
#            queue=queue,
#            )
#    s.apply_async()
#    return txpending_hash_hex


