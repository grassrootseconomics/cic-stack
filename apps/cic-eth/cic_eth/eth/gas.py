# standard imports
import logging

# external imports
import celery
from hexathon import strip_0x
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.chain import ChainSpec
from chainlib.eth.address import is_checksum_address
from chainlib.connection import RPCConnection
from chainqueue.db.enum import StatusBits
from chainlib.eth.gas import (
        balance,
        price,
        )
from chainlib.eth.error import (
        NotFoundEthException,
        EthException,
        )
from chainlib.eth.tx import (
        TxFactory,
        TxFormat,
        unpack,
        )
from chainlib.eth.contract import (
        abi_decode_single,
        ABIContractType,
        )
from chainlib.eth.gas import (
        Gas,
        OverrideGasOracle,
        )
from chainqueue.db.models.tx import TxCache
from chainqueue.db.models.otx import Otx

# local imports
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.base import SessionBase
from cic_eth.error import (
        AlreadyFillingGasError,
        OutOfGasError,
        )
from cic_eth.eth.nonce import CustodialTaskNonceOracle
from cic_eth.queue.tx import (
        queue_create,
        register_tx,
        )
from cic_eth.queue.query import get_tx
from cic_eth.task import (
        CriticalSQLAlchemyTask,
        CriticalSQLAlchemyAndWeb3Task,
        CriticalSQLAlchemyAndSignerTask,
        CriticalWeb3AndSignerTask,
        )

celery_app = celery.current_app
logg = logging.getLogger()


class MaxGasOracle:

    def gas(code=None):
        return 8000000


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
                'cic_eth.eth.gas.check_gas',
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
                'cic_eth.eth.gas.check_gas',
                [
                    chain_spec.asdict(),
                    tx_signed_raws_hex,
                    holder_address,
                    gas,
                    ],
                queue=queue,
                )
    return s_check_gas


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
    tx = unpack(tx_signed_raw_bytes, chain_spec)

    session = SessionBase.create_session()

    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        tx['value'],
        tx['value'],
        session=session,
            )

    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)


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
            'cic_eth.eth.nonce.reserve_nonce',
            [
                address,
                chain_spec_dict,
                gas_provider,
                ],
            queue=queue,
            )
        s_refill_gas = celery.signature(
            'cic_eth.eth.gas.refill_gas',
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
                'cic_eth.queue.state.set_waitforgas',
                [
                    chain_spec_dict,
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
            'cic_eth.eth.nonce.reserve_nonce',
            [
                address,
                chain_spec_dict,
                gas_provider,
                ],
            queue=queue,
            )
        s_refill_gas = celery.signature(
            'cic_eth.eth.gas.refill_gas',
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
            'cic_eth.queue.state.set_ready',
            [
                chain_spec_dict,
                tx_hash,
                ],
            queue=queue,
            )
        ready_tasks.append(s)
    celery.group(ready_tasks)()

    return txs


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
    c = Gas(chain_spec, signer=rpc_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)

    # build and add transaction
    logg.debug('tx send gas amount {} from provider {} to {}'.format(refill_amount, gas_provider, recipient_address))
    (tx_hash_hex, tx_signed_raw_hex) = c.create(gas_provider, recipient_address, refill_amount, tx_format=TxFormat.RLP_SIGNED)
    logg.debug('adding queue refill gas tx {}'.format(tx_hash_hex))
    cache_task = 'cic_eth.eth.gas.cache_gas_data'
    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=cache_task, session=session)

    # add transaction to send queue
    s_status = celery.signature(
        'cic_eth.queue.state.set_ready',
        [
            chain_spec.asdict(),
            tx_hash_hex,
            ],
        queue=queue,
            )
    t = s_status.apply_async()

    return tx_signed_raw_hex


@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def resend_with_higher_gas(self, txold_hash_hex, chain_spec_dict, gas=None, default_factor=1.1):
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

    otx = Otx.load(txold_hash_hex, session)
    if otx == None:
        session.close()
        raise NotLocalTxError(txold_hash_hex)

    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    tx_signed_raw_bytes = bytes.fromhex(otx.signed_tx)
    tx = unpack(tx_signed_raw_bytes, chain_spec)
    logg.debug('resend otx {} {}'.format(tx, otx.signed_tx))

    queue = self.request.delivery_info.get('routing_key')

    logg.debug('before {}'.format(tx))

    rpc = RPCConnection.connect(chain_spec, 'default')
    new_gas_price = gas
    if new_gas_price == None:
        o = price()
        r = rpc.do(o)
        current_gas_price = int(r, 16)
        if tx['gasPrice'] > current_gas_price:
            logg.info('Network gas price {} is lower than overdue tx gas price {}'.format(current_gas_price, tx['gasPrice']))
            #tx['gasPrice'] = int(tx['gasPrice'] * default_factor)
            new_gas_price = tx['gasPrice'] + 1
        else:
            new_gas_price = int(tx['gasPrice'] * default_factor)
            #if gas_price > new_gas_price:
            #    tx['gasPrice'] = gas_price
            #else:
            #    tx['gasPrice'] = new_gas_price


    rpc_signer = RPCConnection.connect(chain_spec, 'signer')
    gas_oracle = OverrideGasOracle(price=new_gas_price, conn=rpc)

    c = TxFactory(chain_spec, signer=rpc_signer, gas_oracle=gas_oracle)
    logg.debug('change gas price from old {} to new {} for tx {}'.format(tx['gasPrice'], new_gas_price, tx))
    tx['gasPrice'] = new_gas_price
    (tx_hash_hex, tx_signed_raw_hex) = c.build_raw(tx)
    queue_create(
        chain_spec,
        tx['nonce'],
        tx['from'],
        tx_hash_hex,
        tx_signed_raw_hex,
        session=session,
            )
    TxCache.clone(txold_hash_hex, tx_hash_hex, session=session)
    session.close()

    s = create_check_gas_task(
            [tx_signed_raw_hex],
            chain_spec, 
            tx['from'],
            tx['gasPrice'] * tx['gas'],
            [tx_hash_hex],
            queue=queue,
            )
    s.apply_async()

    return tx_hash_hex


