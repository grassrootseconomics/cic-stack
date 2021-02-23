# standard imports
import logging

# third-party imports
import celery
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.eth import RpcClient
from cic_eth.queue.tx import create as queue_create

celery_app = celery.current_app
logg = celery_app.log.get_default_logger()


@celery_app.task()
def sign_tx(tx, chain_str):
    """Sign a single transaction against the given chain specification.

    :param tx: Transaction in standard Ethereum format
    :type tx: dict
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Transaction hash and raw signed transaction, respectively
    :rtype: tuple
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)
    tx_transfer_signed = c.w3.eth.sign_transaction(tx) 
    logg.debug('tx_transfer_signed {}'.format(tx_transfer_signed))
    tx_hash = c.w3.keccak(hexstr=tx_transfer_signed['raw'])
    tx_hash_hex = tx_hash.hex()
    return (tx_hash_hex, tx_transfer_signed['raw'],)


def sign_and_register_tx(tx, chain_str, queue, cache_task=None):
    """Signs the provided transaction, and adds it to the transaction queue cache (with status PENDING).

    :param tx: Standard ethereum transaction data
    :type tx: dict
    :param chain_str: Chain spec, string representation
    :type chain_str: str
    :param queue: Task queue
    :type queue: str
    :param cache_task: Cache task to call with signed transaction. If None, no task will be called.
    :type cache_task: str
    :raises: sqlalchemy.exc.DatabaseError
    :returns: Tuple; Transaction hash, signed raw transaction data
    :rtype: tuple
    """
    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)

    logg.debug('adding queue tx {}'.format(tx_hash_hex))

    queue_create(
        tx['nonce'],
        tx['from'],
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_str,
    )        

    if cache_task != None:
        logg.debug('adding cache task {} tx {}'.format(cache_task, tx_hash_hex))
        s_cache = celery.signature(
                cache_task,
                [
                    tx_hash_hex,
                    tx_signed_raw_hex,
                    chain_str,
                    ],
                queue=queue,
                )
        s_cache.apply_async()

    return (tx_hash_hex, tx_signed_raw_hex,)


# TODO: rename as we will not be sending task in the chain, this is the responsibility of the dispatcher
def create_check_gas_and_send_task(tx_signed_raws_hex, chain_str, holder_address, gas, tx_hashes_hex=None, queue=None):
    """Creates a celery task signature for a check_gas task that adds the task to the outgoing queue to be processed by the dispatcher.

    If tx_hashes_hex is not spefified, a preceding task chained to check_gas must supply the transaction hashes as its return value.

    :param tx_signed_raws_hex: Raw signed transaction data
    :type tx_signed_raws_hex: list of str, 0x-hex
    :param chain_str: Chain spec, string representation
    :type chain_str: str
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
                    chain_str,
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
                    chain_str,
                    tx_signed_raws_hex,
                    holder_address,
                    gas,
                    ],
                queue=queue,
                )
    return s_check_gas
