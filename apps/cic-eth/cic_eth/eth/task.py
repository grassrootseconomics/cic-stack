# standard imports
import logging

# external imports
import sha3
import celery
from chainlib.chain import ChainSpec
from chainlib.eth.sign import sign_transaction
from chainlib.connection import RPCConnection
from chainlib.eth.tx import unpack
from hexathon import (
        strip_0x,
        add_0x,
        )

# local imports
from cic_eth.eth import RpcClient
from cic_eth.queue.tx import create as queue_create
from cic_eth.error import SignerError

celery_app = celery.current_app
logg = celery_app.log.get_default_logger()

#
#@celery_app.task()
#def sign_tx(tx, chain_str):
#    """Sign a single transaction against the given chain specification.
#
#    :param tx: Transaction in standard Ethereum format
#    :type tx: dict
#    :param chain_str: Chain spec string representation
#    :type chain_str: str
#    :returns: Transaction hash and raw signed transaction, respectively
#    :rtype: tuple
#    """
#    chain_spec = ChainSpec.from_chain_str(chain_str)
#    #c = RpcClient(chain_spec)
#    tx_transfer_signed = None
#    conn = RPCConnection.connect('signer')
#    try:
#        o = sign_transaction(tx)
#        tx_transfer_signed = conn.do(o)
#    #try:
#    #    tx_transfer_signed = c.w3.eth.sign_transaction(tx)
#    except Exception as e:
#        raise SignerError('sign tx {}: {}'.format(tx, e))
#    logg.debug('tx_transfer_signed {}'.format(tx_transfer_signed))
#    h = sha3.keccak_256()
#    h.update(bytes.fromhex(strip_0x(tx_transfer_signed['raw'])))
#    tx_hash = h.digest()
#    #tx_hash = c.w3.keccak(hexstr=tx_transfer_signed['raw'])
#    tx_hash_hex = add_0x(tx_hash.hex())
#    return (tx_hash_hex, tx_transfer_signed['raw'],)


#def sign_and_register_tx(tx, chain_str, queue, cache_task=None, session=None):
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
    #(tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)

    logg.debug('adding queue tx {}'.format(tx_hash_hex))
    tx_signed_raw = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw, chain_id=chain_spec.chain_id())

    queue_create(
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

    return (tx_hash_hex, tx_signed_raw_hex,)


# TODO: rename as we will not be sending task in the chain, this is the responsibility of the dispatcher
def create_check_gas_task(tx_signed_raws_hex, chain_spec, holder_address, gas=None, tx_hashes_hex=None, queue=None):
    """Creates a celery task signature for a check_gas task that adds the task to the outgoing queue to be processed by the dispatcher.

    If tx_hashes_hex is not spefified, a preceding task chained to check_gas must supply the transaction hashes as its return value.

    :param tx_signed_raws_hex: Raw signed transaction data
    :type tx_signed_raws_hex: list of str, 0x-hex
    :param chain_spec: Chain spec of address to add check gas for
    :type chain_spec: chainlib.chain.ChainSpec
    :param holder_address: Address sending the transactions
    :type holder_address: str, 0x-hex
    :param gas: Gas budget hint for transactions
    :type gas: int
    :param tx_hashes_hex: Transaction hashes
    :type tx_hashes_hex: list of str, 0x-hex
    :param queue: Task queue
    :type queue: str
    :returns: Signature of task chain
    :rtype: celery.Signature
    """
    s_check_gas = None
    if tx_hashes_hex != None:
        s_check_gas = celery.signature(
                'cic_eth.eth.tx.check_gas',
                [
                    tx_hashes_hex,
                    chain_spec.asdict(),
                    tx_signed_raws_hex,
                    holder_address,
                    gas,
                    ],
                queue=queue,
                )
    else:
        s_check_gas = celery.signature(
                'cic_eth.eth.tx.check_gas',
                [
                    chain_spec.asdict(),
                    tx_signed_raws_hex,
                    holder_address,
                    gas,
                    ],
                queue=queue,
                )
    return s_check_gas
