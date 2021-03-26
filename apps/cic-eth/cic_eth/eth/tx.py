# standard imports
import logging

# third-party imports
import celery
import requests
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.chain import ChainSpec
from chainlib.eth.address import is_checksum_address
from chainlib.eth.gas import balance
from chainlib.eth.error import (
        EthException,
        NotFoundEthException,
        )
from chainlib.eth.tx import (
        transaction,
        receipt,
        raw,
        TxFormat,
        unpack,
        )
from chainlib.connection import RPCConnection
from chainlib.hash import keccak256_hex_to_hex
from chainlib.eth.gas import Gas
from chainlib.eth.contract import (
        abi_decode_single,
        ABIContractType,
        )
from hexathon import (
        add_0x,
        strip_0x,
        )

# local imports
from cic_eth.db import (
        Otx,
        SessionBase,
        )
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
#from cic_eth.queue.tx import create as queue_create
from cic_eth.queue.tx import (
        get_tx,
        register_tx,
        get_nonce_tx,
        )
from cic_eth.error import OutOfGasError
from cic_eth.error import LockedError
from cic_eth.eth.gas import (
        create_check_gas_task,
        )
from cic_eth.eth.nonce import CustodialTaskNonceOracle
from cic_eth.error import (
        AlreadyFillingGasError,
        EthError,
        )
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
def check_gas(self, tx_hashes, chain_spec_dict, txs=[], address=None, gas_required=None):
    """Check the gas level of the sender address of a transaction.

    If the account balance is not sufficient for the required gas, gas refill is requested and OutOfGasError raiser.

    If account balance is sufficient, but level of gas before spend is below "safe" threshold, gas refill is requested, and execution continues normally.

    :param tx_hashes: Transaction hashes due to be submitted
    :type tx_hashes: list of str, 0x-hex
    :param chain_spec_dict: Chain spec dict representation
    :type chain_spec_dict: dict
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

    #if not web3.Web3.isChecksumAddress(address):
    if not is_checksum_address(address):
        raise ValueError('invalid address {}'.format(address))

    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    queue = self.request.delivery_info.get('routing_key')

    conn = RPCConnection.connect(chain_spec)

    # TODO: it should not be necessary to pass address explicitly, if not passed should be derived from the tx
    gas_balance = 0
    try:
        o = balance(address)
        r = conn.do(o)
        conn.disconnect()
        gas_balance = abi_decode_single(ABIContractType.UINT256, r)
    except EthException as e:
        conn.disconnect()
        raise EthError('gas_balance call for {}: {}'.format(address, e))

    logg.debug('address {} has gas {} needs {}'.format(address, gas_balance, gas_required))
    session = SessionBase.create_session()
    gas_provider = AccountRole.get_address('GAS_GIFTER', session=session)
    session.close()

    if gas_required > gas_balance:
        s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                address,
                gas_provider,
                ],
            queue=queue,
            )
        s_refill_gas = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                chain_spec_dict,
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
        raise OutOfGasError('need to fill gas, required {}, had {}'.format(gas_required, gas_balance))

    safe_gas = self.safe_gas_threshold_amount
    if gas_balance < safe_gas:
        s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                address,
                gas_provider,
                ],
            queue=queue,
            )
        s_refill_gas = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                chain_spec_dict,
                ],
            queue=queue,
                )
        s_nonce.link(s_refill_gas)
        s_nonce.apply_async()
        logg.debug('requested refill from {} to {}'.format(gas_provider, address))
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

    tx_hex = txs[0]
    logg.debug('send transaction {}'.format(tx_hex))

    tx_hash_hex = add_0x(keccak256_hex_to_hex(tx_hex))

    queue = self.request.delivery_info.get('routing_key')

    r = None
    s_set_sent = celery.signature(
        'cic_eth.queue.tx.set_sent_status',
        [
            tx_hash_hex,
            False
            ],
            queue=queue,
        )

    o = raw(tx_hex)
    conn = RPCConnection.connect(chain_spec, 'default')
    conn.do(o)
    s_set_sent.apply_async()

    tx_tail = txs[1:]
    if len(tx_tail) > 0:
        s = celery.signature(
            'cic_eth.eth.tx.send',
            [tx_tail],
            queue=queue,
                )
        s.apply_async()

    return tx_hash_hex


# TODO: if this method fails the nonce will be out of sequence. session needs to be extended to include the queue create, so that nonce is rolled back if the second sql query fails. Better yet, split each state change into separate tasks.
# TODO: method is too long, factor out code for clarity
@celery_app.task(bind=True, throws=(NotFoundEthException,), base=CriticalWeb3AndSignerTask)
def refill_gas(self, recipient_address, chain_spec_dict):
    """Executes a native token transaction to fund the recipient's gas expenditures.

    :param recipient_address: Recipient in need of gas
    :type recipient_address: str, 0x-hex
    :param chain_str: Chain spec, string representation
    :type chain_str: str
    :raises AlreadyFillingGasError: A gas refill transaction for this address is already executing
    :returns: Transaction hash.
    :rtype: str, 0x-hex
    """
    # essentials
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    queue = self.request.delivery_info.get('routing_key')

    # Determine value of gas tokens to send
    # if an uncompleted gas refill for the same recipient already exists, we still need to spend the nonce
    # however, we will perform a 0-value transaction instead
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
        logg.warning('already filling gas {}'.format(str(AlreadyFillingGasError(recipient_address))))
        zero_amount = True
    session.flush()

    # finally determine the value to send
    refill_amount = 0
    if not zero_amount:
        refill_amount = self.safe_gas_refill_amount

    # determine sender
    gas_provider = AccountRole.get_address('GAS_GIFTER', session=session)
    session.flush()

    # set up evm RPC connection
    rpc = RPCConnection.connect(chain_spec, 'default')

    # set up transaction builder
    nonce_oracle = CustodialTaskNonceOracle(gas_provider, self.request.root_id, session=session)
    gas_oracle = self.create_gas_oracle(rpc)
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')
    c = Gas(signer=rpc_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=chain_spec.chain_id())

    # build and add transaction
    logg.debug('tx send gas amount {} from provider {} to {}'.format(refill_amount, gas_provider, recipient_address))
    (tx_hash_hex, tx_signed_raw_hex) = c.create(gas_provider, recipient_address, refill_amount, tx_format=TxFormat.RLP_SIGNED)
    logg.debug('adding queue refill gas tx {}'.format(tx_hash_hex))
    cache_task = 'cic_eth.eth.tx.cache_gas_data'
    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=cache_task, session=session)

    # add transaction to send queue
    s_status = celery.signature(
        'cic_eth.queue.tx.set_ready',
        [
            tx_hash_hex,
            ],
        queue=queue,
            )
    t = s_status.apply_async()

    return tx_signed_raw_hex


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
    tx = unpack(tx_signed_raw_bytes, chain_spec.chain_id())
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
def reserve_nonce(self, chained_input, signer_address=None):

    session = SessionBase.create_session()

    address = None
    if signer_address == None:
        address = chained_input
        logg.debug('non-explicit address for reserve nonce, using arg head {}'.format(chained_input))
    else:
        #if web3.Web3.isChecksumAddress(signer_address):
        if is_checksum_address(signer_address):
            address = signer_address
            logg.debug('explicit address for reserve nonce {}'.format(signer_address))
        else:
            address = AccountRole.get_address(signer_address, session=session)
            logg.debug('role for reserve nonce {} -> {}'.format(signer_address, address))

    if not is_checksum_address(address):
        raise ValueError('invalid result when resolving address for nonce {}'.format(address))

    root_id = self.request.root_id
    nonce = NonceReservation.next(address, root_id)

    session.commit()

    session.close()

    return chained_input


@celery_app.task(bind=True, throws=(NotFoundEthException,), base=CriticalWeb3Task)
def sync_tx(self, tx_hash_hex, chain_spec_dict):
    """Force update of network status of a simgle transaction

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
#    tx = unpack_signed_raw_tx(tx_signed_bytes, chain_spec.chain_id())
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


# TODO: Move to cic_eth.eth.gas
@celery_app.task(base=CriticalSQLAlchemyTask)
def cache_gas_data(
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_spec_dict,
        ):
    """Helper function for otx_cache_parse_tx

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx: Signed raw transaction
    :type tx: str, 0x-hex
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw_bytes, chain_spec.chain_id())

    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        tx['value'],
        tx['value'],
            )

    session = SessionBase.create_session()
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)
