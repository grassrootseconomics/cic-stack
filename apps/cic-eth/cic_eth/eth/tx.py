# standard imports
import logging

# third-party imports
import celery
import requests
import web3
from cic_registry import zero_address
from cic_registry.chain import ChainSpec

# local imports
from .rpc import RpcClient
from cic_eth.db import Otx, SessionBase
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.nonce import NonceReservation
from cic_eth.db.models.lock import Lock
from cic_eth.db.models.role import AccountRole
from cic_eth.db.enum import (
        LockEnum,
        StatusBits,
        )
from cic_eth.error import PermanentTxError
from cic_eth.error import TemporaryTxError
from cic_eth.error import NotLocalTxError
from cic_eth.queue.tx import create as queue_create
from cic_eth.queue.tx import get_tx
from cic_eth.queue.tx import get_nonce_tx
from cic_eth.error import OutOfGasError
from cic_eth.error import LockedError
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.task import sign_and_register_tx, create_check_gas_and_send_task
from cic_eth.eth.task import sign_tx
from cic_eth.eth.nonce import NonceOracle
from cic_eth.error import AlreadyFillingGasError
from cic_eth.eth.util import tx_hex_string
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


# TODO this function is too long
@celery_app.task(bind=True, throws=(OutOfGasError), base=CriticalSQLAlchemyAndWeb3Task)
def check_gas(self, tx_hashes, chain_str, txs=[], address=None, gas_required=None):
    """Check the gas level of the sender address of a transaction.

    If the account balance is not sufficient for the required gas, gas refill is requested and OutOfGasError raiser.

    If account balance is sufficient, but level of gas before spend is below "safe" threshold, gas refill is requested, and execution continues normally.

    :param tx_hashes: Transaction hashes due to be submitted
    :type tx_hashes: list of str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param txs: Signed raw transaction data, corresponding to tx_hashes
    :type txs: list of str, 0x-hex
    :param address: Sender address
    :type address: str, 0x-hex
    :param gas_required: Gas limit * gas price for transaction, (optional, if not set will be retrived from transaction data)
    :type gas_required: int
    :return: Signed raw transaction data list
    :rtype: param txs, unchanged
    """
    if len(txs) == 0:
        for i in range(len(tx_hashes)):
            o = get_tx(tx_hashes[i])
            txs.append(o['signed_tx'])
            if address == None:
                address = o['address']

    if not web3.Web3.isChecksumAddress(address):
        raise ValueError('invalid address {}'.format(address))

    chain_spec = ChainSpec.from_chain_str(chain_str)

    queue = self.request.delivery_info['routing_key']

    #c = RpcClient(chain_spec, holder_address=address)
    c = RpcClient(chain_spec)

    # TODO: it should not be necessary to pass address explicitly, if not passed should be derived from the tx
    balance = 0
    try:
        balance = c.w3.eth.getBalance(address) 
    except ValueError as e:
        raise EthError('balance call for {}'.format())

    logg.debug('address {} has gas {} needs {}'.format(address, balance, gas_required))

    if gas_required > balance:
        s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                address,
                c.gas_provider(),
                ],
            queue=queue,
            )
        s_refill_gas = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                chain_str,
                ],
            queue=queue,
                )
        s_nonce.link(s_refill_gas)
        s_nonce.apply_async()
        wait_tasks = []
        for tx_hash in tx_hashes:
            s = celery.signature(
                'cic_eth.queue.tx.set_waitforgas',
                [
                    tx_hash,
                    ],
                queue=queue,
                )
            wait_tasks.append(s)
        celery.group(wait_tasks)()
        raise OutOfGasError('need to fill gas, required {}, had {}'.format(gas_required, balance))

    safe_gas = c.safe_threshold_amount()
    if balance < safe_gas:
        s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                address,
                c.gas_provider(),
                ],
            queue=queue,
            )
        s_refill_gas = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                chain_str,
                ],
            queue=queue,
                )
        s_nonce.link(s_refill)
        s_nonce.apply_async()
        logg.debug('requested refill from {} to {}'.format(c.gas_provider(), address))
    ready_tasks = []
    for tx_hash in tx_hashes:
        s = celery.signature(
            'cic_eth.queue.tx.set_ready',
            [
                tx_hash,
                ],
            queue=queue,
            )
        ready_tasks.append(s)
    celery.group(ready_tasks)()

    return txs


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

    queue = self.request.delivery_info['routing_key']

    #otxs = ','.format("'{}'".format(tx_hash) for tx_hash in tx_hashes)

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


# TODO: Move this and send to subfolder submodule
class ParityNodeHandler:
    def __init__(self, chain_spec, queue):
        self.chain_spec = chain_spec
        self.chain_str = str(chain_spec)
        self.queue = queue

    def handle(self, exception, tx_hash_hex, tx_hex):
        meth = self.handle_default
        if isinstance(exception, (ValueError)):
            
            earg = exception.args[0]
            if earg['code'] == -32010:
                logg.debug('skipping lock for code {}'.format(earg['code']))
                meth = self.handle_invalid_parameters
            elif earg['code'] == -32602:
                meth = self.handle_invalid_encoding
            else:
                # TODO: move to status log db comment field
                meth = self.handle_invalid
        elif isinstance(exception, (requests.exceptions.ConnectionError)):
            meth = self.handle_connection
        (t, e_fn, message) = meth(tx_hash_hex, tx_hex, str(exception))
        return (t, e_fn, '{} {}'.format(message, exception))
           

    def handle_connection(self, tx_hash_hex, tx_hex, debugstr=None):
        s_set_sent = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [
                tx_hash_hex,
                True,
                ],
            queue=self.queue,
            )
        t = s_set_sent.apply_async()
        return (t, TemporaryTxError, 'Sendfail {}'.format(tx_hex_string(tx_hex, self.chain_spec.chain_id())))


    def handle_invalid_encoding(self, tx_hash_hex, tx_hex, debugstr=None):
        tx_bytes = bytes.fromhex(tx_hex[2:])
        tx = unpack_signed_raw_tx(tx_bytes, self.chain_spec.chain_id())
        s_lock = celery.signature(
            'cic_eth.admin.ctrl.lock_send',
            [
                tx_hash_hex,
                self.chain_str,
                tx['from'],
                tx_hash_hex,
                ],
            queue=self.queue,
            )
        s_set_reject = celery.signature(
            'cic_eth.queue.tx.set_rejected',
            [],
            queue=self.queue,
            )
        nonce_txs = get_nonce_tx(tx['nonce'], tx['from'], self.chain_spec.chain_id())
        attempts = len(nonce_txs)
        if attempts < MAX_NONCE_ATTEMPTS:
            logg.debug('nonce {} address {} retries {} < {}'.format(tx['nonce'], tx['from'], attempts, MAX_NONCE_ATTEMPTS))
            s_resend = celery.signature(
                    'cic_eth.eth.tx.resend_with_higher_gas',
                    [
                        self.chain_str,
                        None,
                        1.01,
                        ],
                    queue=self.queue,
                    )
            s_unlock = celery.signature(
                    'cic_eth.admin.ctrl.unlock_send',
                    [
                        self.chain_str,
                        tx['from'],
                        ],
                    queue=self.queue,
                    )
            s_resend.link(s_unlock)
            s_set_reject.link(s_resend)

        s_lock.link(s_set_reject)
        t = s_lock.apply_async()
        return (t, PermanentTxError, 'Reject invalid encoding {}'.format(tx_hex_string(tx_hex, self.chain_spec.chain_id())))


    def handle_invalid_parameters(self, tx_hash_hex, tx_hex, debugstr=None):
        s_sync = celery.signature(
            'cic_eth.eth.tx.sync_tx',
            [
                tx_hash_hex,
                self.chain_str,
                ],
            queue=self.queue,
            )
        t = s_sync.apply_async()
        return (t, PermanentTxError, 'Reject invalid parameters {}'.format(tx_hex_string(tx_hex, self.chain_spec.chain_id())))


    def handle_invalid(self, tx_hash_hex, tx_hex, debugstr=None):
        tx_bytes = bytes.fromhex(tx_hex[2:])
        tx = unpack_signed_raw_tx(tx_bytes, self.chain_spec.chain_id())
        s_lock = celery.signature(
            'cic_eth.admin.ctrl.lock_send',
            [
                tx_hash_hex,
                self.chain_str,
                tx['from'],
                tx_hash_hex,
                ],
            queue=self.queue,
            )
        s_set_reject = celery.signature(
            'cic_eth.queue.tx.set_rejected',
            [],
            queue=self.queue,
            )
        s_debug = celery.signature(
            'cic_eth.admin.debug.alert',
            [
                tx_hash_hex,
                debugstr,
                ],
            queue=self.queue,
            )
        s_set_reject.link(s_debug)
        s_lock.link(s_set_reject)
        t = s_lock.apply_async()
        return (t, PermanentTxError, 'Reject invalid {}'.format(tx_hex_string(tx_hex, self.chain_spec.chain_id())))


    def handle_default(self, tx_hash_hex, tx_hex, debugstr):
        tx_bytes = bytes.fromhex(tx_hex[2:])
        tx = unpack_signed_raw_tx(tx_bytes, self.chain_spec.chain_id())
        s_lock = celery.signature(
                'cic_eth.admin.ctrl.lock_send',
                [
                    tx_hash_hex,
                    self.chain_str,
                    tx['from'],
                    tx_hash_hex,
                    ],
                queue=self.queue,
                )
        s_set_fubar = celery.signature(
            'cic_eth.queue.tx.set_fubar',
            [],
            queue=self.queue,
            )
        s_debug = celery.signature(
            'cic_eth.admin.debug.alert',
            [
                tx_hash_hex,
                debugstr,
                ],
            queue=self.queue,
            )
        s_set_fubar.link(s_debug)
        s_lock.link(s_set_fubar)
        t = s_lock.apply_async()
        return (t, PermanentTxError, 'Fubar {} {}'.format(tx_hex_string(tx_hex, self.chain_spec.chain_id()), debugstr))


# TODO: A lock should be introduced to ensure that the send status change and the transaction send is atomic.
@celery_app.task(bind=True, base=CriticalWeb3Task)
def send(self, txs, chain_str):
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

    chain_spec = ChainSpec.from_chain_str(chain_str)

    tx_hex = txs[0]
    logg.debug('send transaction {}'.format(tx_hex))

    tx_hash = web3.Web3.keccak(hexstr=tx_hex)
    tx_hash_hex = tx_hash.hex()

    queue = self.request.delivery_info.get('routing_key', None)

    c = RpcClient(chain_spec)
    r = None
    s_set_sent = celery.signature(
        'cic_eth.queue.tx.set_sent_status',
        [
            tx_hash_hex,
            False
            ],
            queue=queue,
        )
    try:
        r = c.w3.eth.send_raw_transaction(tx_hex)
    except requests.exceptions.ConnectionError as e:
        raise(e)
    except Exception as e:
        raiser = ParityNodeHandler(chain_spec, queue)
        (t, e, m) = raiser.handle(e, tx_hash_hex, tx_hex)
        raise e(m)
    s_set_sent.apply_async()

    tx_tail = txs[1:]
    if len(tx_tail) > 0:
        s = celery.signature(
            'cic_eth.eth.tx.send',
            [tx_tail],
            queue=queue,
                )
        s.apply_async()

    return r.hex()


# TODO: if this method fails the nonce will be out of sequence. session needs to be extended to include the queue create, so that nonce is rolled back if the second sql query fails. Better yet, split each state change into separate tasks.
# TODO: method is too long, factor out code for clarity
@celery_app.task(bind=True, throws=(web3.exceptions.TransactionNotFound,), base=CriticalWeb3AndSignerTask)
def refill_gas(self, recipient_address, chain_str):
    """Executes a native token transaction to fund the recipient's gas expenditures.

    :param recipient_address: Recipient in need of gas
    :type recipient_address: str, 0x-hex
    :param chain_str: Chain spec, string representation
    :type chain_str: str
    :raises AlreadyFillingGasError: A gas refill transaction for this address is already executing
    :returns: Transaction hash.
    :rtype: str, 0x-hex
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)

    zero_amount = False
    session = SessionBase.create_session()
    status_filter = StatusBits.FINAL | StatusBits.NODE_ERROR | StatusBits.NETWORK_ERROR | StatusBits.UNKNOWN_ERROR
    q = session.query(Otx.tx_hash)
    q = q.join(TxCache)
    q = q.filter(Otx.status.op('&')(StatusBits.FINAL.value)==0)
    q = q.filter(TxCache.from_value!=0)
    q = q.filter(TxCache.recipient==recipient_address)
    c = q.count()
    if c > 0:
        #session.close()
        #raise AlreadyFillingGasError(recipient_address)
        logg.warning('already filling gas {}'.format(str(AlreadyFillingGasError(recipient_address))))
        zero_amount = True
    session.flush()

    queue = self.request.delivery_info['routing_key']

    c = RpcClient(chain_spec)
    clogg = celery_app.log.get_default_logger()
    logg.debug('refill gas from provider address {}'.format(c.gas_provider()))
    default_nonce = c.w3.eth.getTransactionCount(c.gas_provider(), 'pending')
    nonce_generator = NonceOracle(c.gas_provider(), default_nonce)
    #nonce = nonce_generator.next(session=session)
    nonce = nonce_generator.next_by_task_uuid(self.request.root_id, session=session)
    gas_price = c.gas_price()
    gas_limit = c.default_gas_limit
    refill_amount = 0
    if not zero_amount:
        refill_amount = c.refill_amount()
    logg.debug('tx send gas price {} nonce {}'.format(gas_price, nonce))

    # create and sign transaction
    tx_send_gas = {
                'from': c.gas_provider(),
                'to': recipient_address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'chainId': chain_spec.chain_id(),
                'nonce': nonce,
                'value': refill_amount,
                'data': '',
            }
    tx_send_gas_signed = c.w3.eth.sign_transaction(tx_send_gas)
    tx_hash = web3.Web3.keccak(hexstr=tx_send_gas_signed['raw'])
    tx_hash_hex = tx_hash.hex()

    # TODO: route this through sign_and_register_tx instead
    logg.debug('adding queue refill gas tx {}'.format(tx_hash_hex))
    queue_create(
        nonce,
        c.gas_provider(),
        tx_hash_hex,
        tx_send_gas_signed['raw'],
        chain_str,
        session=session,
        )
    session.close()

    s_tx_cache = celery.signature(
            'cic_eth.eth.tx.cache_gas_refill_data',
            [
                tx_hash_hex,
                tx_send_gas,
                ],
            queue=queue,
            )
    s_status = celery.signature(
        'cic_eth.queue.tx.set_ready',
        [
            tx_hash_hex,
            ],
        queue=queue,
            )
    celery.group(s_tx_cache, s_status)()

    return tx_send_gas_signed['raw']


@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def resend_with_higher_gas(self, txold_hash_hex, chain_str, gas=None, default_factor=1.1):
    """Create a new transaction from an existing one with same nonce and higher gas price.

    :param txold_hash_hex: Transaction to re-create
    :type txold_hash_hex: str, 0x-hex
    :param chain_str: Chain spec, string representation
    :type chain_str: str
    :param gas: Explicitly use the specified gas amount
    :type gas: number
    :param default_factor: Default factor by which to increment the gas price by
    :type default_factor: float
    :raises NotLocalTxError: Transaction does not exist in the local queue
    :returns: Transaction hash
    :rtype: str, 0x-hex
    """
    session = SessionBase.create_session()

    
    q = session.query(Otx)
    q = q.filter(Otx.tx_hash==txold_hash_hex)
    otx = q.first()
    if otx == None:
        session.close()
        raise NotLocalTxError(txold_hash_hex)

    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)

    tx_signed_raw_bytes = bytes.fromhex(otx.signed_tx[2:])
    tx = unpack_signed_raw_tx(tx_signed_raw_bytes, chain_spec.chain_id())
    logg.debug('resend otx {} {}'.format(tx, otx.signed_tx))

    queue = self.request.delivery_info['routing_key']

    logg.debug('before {}'.format(tx))
    if gas != None:
        tx['gasPrice'] = gas
    else:
        gas_price = c.gas_price()
        if tx['gasPrice'] > gas_price:
            logg.info('Network gas price {} is lower than overdue tx gas price {}'.format(gas_price, tx['gasPrice']))
            #tx['gasPrice'] = int(tx['gasPrice'] * default_factor)
            tx['gasPrice'] += 1
        else:
            new_gas_price = int(tx['gasPrice'] * default_factor)
            if gas_price > new_gas_price:
                tx['gasPrice'] = gas_price
            else:
                tx['gasPrice'] = new_gas_price

    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx, chain_str)
    queue_create(
        tx['nonce'],
        tx['from'],
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_str,
        session=session,
            )
    TxCache.clone(txold_hash_hex, tx_hash_hex, session=session)
    session.close()

    s = create_check_gas_and_send_task(
            [tx_signed_raw_hex],
            chain_str, 
            tx['from'],
            tx['gasPrice'] * tx['gas'],
            [tx_hash_hex],
            queue=queue,
            )
    s.apply_async()

    return tx_hash_hex


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def reserve_nonce(self, chained_input, signer=None):
    session = SessionBase.create_session()

    address = None
    if signer == None:
        address = chained_input
        logg.debug('non-explicit address for reserve nonce, using arg head {}'.format(chained_input))
    else:
        if web3.Web3.isChecksumAddress(signer):
            address = signer
            logg.debug('explicit address for reserve nonce {}'.format(signer))
        else:
            address = AccountRole.get_address(signer, session=session)
            logg.debug('role for reserve nonce {} -> {}'.format(signer, address))

    if not web3.Web3.isChecksumAddress(address):
        raise ValueError('invalid result when resolving address for nonce {}'.format(address))

    root_id = self.request.root_id
    nonce = NonceReservation.next(address, root_id)

    session.close()

    return chained_input


@celery_app.task(bind=True, throws=(web3.exceptions.TransactionNotFound,), base=CriticalWeb3Task)
def sync_tx(self, tx_hash_hex, chain_str):
    """Force update of network status of a simgle transaction

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    """

    queue = self.request.delivery_info['routing_key']

    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)

    tx = c.w3.eth.getTransaction(tx_hash_hex)
    rcpt = None
    try:
        rcpt = c.w3.eth.getTransactionReceipt(tx_hash_hex)
    except web3.exceptions.TransactionNotFound as e:
        pass

    if rcpt != None:
        success = rcpt['status'] == 1
        logg.debug('sync tx {} mined block {} success {}'.format(tx_hash_hex, rcpt['blockNumber'], success))

        s = celery.signature(
            'cic_eth.queue.tx.set_final_status',
            [
                tx_hash_hex,
                rcpt['blockNumber'],
                not success,
                ],
                queue=queue,
            )
    else:
        logg.debug('sync tx {} mempool'.format(tx_hash_hex))

        s = celery.signature(
            'cic_eth.queue.tx.set_sent_status',
            [
                tx_hash_hex,
                ],
                queue=queue,
            )

    s.apply_async()



@celery_app.task(bind=True)
def resume_tx(self, txpending_hash_hex, chain_str):
    """Queue a suspended tranaction for (re)sending

    :param txpending_hash_hex: Transaction hash
    :type txpending_hash_hex: str, 0x-hex
    :param chain_str: Chain spec, string representation
    :type chain_str: str
    :raises NotLocalTxError: Transaction does not exist in the local queue
    :returns: Transaction hash
    :rtype: str, 0x-hex
    """

    chain_spec = ChainSpec.from_chain_str(chain_str)

    session = SessionBase.create_session()
    q = session.query(Otx.signed_tx)
    q = q.filter(Otx.tx_hash==txpending_hash_hex)
    r = q.first()
    session.close()
    if r == None:
        raise NotLocalTxError(txpending_hash_hex)

    tx_signed_raw_hex = r[0]
    tx_signed_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    tx = unpack_signed_raw_tx(tx_signed_bytes, chain_spec.chain_id())

    queue = self.request.delivery_info['routing_key']

    s = create_check_gas_and_send_task(
            [tx_signed_raw_hex],
            chain_str,
            tx['from'],
            tx['gasPrice'] * tx['gas'],
            [txpending_hash_hex],
            queue=queue,
            )
    s.apply_async()
    return txpending_hash_hex


@celery_app.task(base=CriticalSQLAlchemyTask)
def otx_cache_parse_tx(
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_str,
        ):
    """Generates and commits transaction cache metadata for a gas refill transaction

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx_signed_raw_hex: Raw signed transaction
    :type tx_signed_raw_hex: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """


    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)
    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    tx = unpack_signed_raw_tx(tx_signed_raw_bytes, chain_spec.chain_id())
    (txc, cache_id) = cache_gas_refill_data(tx_hash_hex, tx)
    return txc


@celery_app.task(base=CriticalSQLAlchemyTask)
def cache_gas_refill_data(
        tx_hash_hex,
        tx,
        ):
    """Helper function for otx_cache_parse_tx

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx: Signed raw transaction
    :type tx: str, 0x-hex
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        zero_address,
        zero_address,
        tx['value'],
        tx['value'],
            )

    session = SessionBase.create_session()
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)
