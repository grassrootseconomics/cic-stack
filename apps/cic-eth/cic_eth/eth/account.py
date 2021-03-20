# standard imports
import logging

# external imports
import celery
from erc20_single_shot_faucet import Faucet
from chainlib.eth.constant import ZERO_ADDRESS
from hexathon import strip_0x
from chainlib.connection import RPCConnection
from chainlib.eth.sign import (
        new_account,
        sign_message,
        )
from chainlib.eth.address import to_checksum_address
from chainlib.eth.tx import TxFormat 
from chainlib.chain import ChainSpec
from eth_accounts_index import AccountRegistry

# local import
#from cic_eth.registry import safe_registry
#from cic_eth.eth import RpcClient
from cic_eth_registry import CICRegistry
from cic_eth.eth import registry_extra_identifiers
from cic_eth.eth.gas import (
        create_check_gas_task,
        )
#from cic_eth.eth.factory import TxFactory
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.tx import TxCache
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.error import (
        RoleMissingError,
        SignerError,
        )
from cic_eth.task import (
        CriticalSQLAlchemyTask,
        CriticalSQLAlchemyAndSignerTask,
        BaseTask,
        )
from cic_eth.eth.nonce import (
        CustodialTaskNonceOracle,
        )
from cic_eth.queue.tx import (
        register_tx,
        )

logg = logging.getLogger()
celery_app = celery.current_app 


def unpack_register(data):
    """Verifies that a transaction is an "AccountRegister.add" transaction, and extracts call parameters from it.

    :param data: Raw input data from Ethereum transaction.
    :type data: str, 0x-hex
    :raises ValueError: Function signature does not match AccountRegister.add
    :returns: Parsed parameters
    :rtype: dict
    """
    data = strip_0x(data)
    f = data[:8]
    if f != '0a3b0a4f':
        raise ValueError('Invalid account index register data ({})'.format(f))

    d = data[8:]
    return {
        'to': to_checksum_address(d[64-40:64]),
        }


def unpack_gift(data):
    """Verifies that a transaction is a "Faucet.giveTo" transaction, and extracts call parameters from it.

    :param data: Raw input data from Ethereum transaction.
    :type data: str, 0x-hex
    :raises ValueError: Function signature does not match AccountRegister.add
    :returns: Parsed parameters
    :rtype: dict
    """
    data = strip_0x(data)
    f = data[:8]
    if f != '63e4bff4':
        raise ValueError('Invalid gift data ({})'.format(f))

    d = data[8:]
    return {
        'to': to_checksum_address(d[64-40:64]),
        }
     

# TODO: Separate out nonce initialization task
@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def create(self, password, chain_str):
    """Creates and stores a new ethereum account in the keystore.

    The password is passed on to the wallet backend, no encryption is performed in the task worker.

    :param password: Password to encrypt private key with
    :type password: str
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Ethereum address of newly created account
    :rtype: str, 0x-hex
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)
    #c = RpcClient(chain_spec)
    a = None
    conn = RPCConnection.connect(chain_spec, 'signer')
    o = new_account()
    a = conn.do(o)

    if a == None:
        raise SignerError('create account')
    logg.debug('created account {}'.format(a))

    # Initialize nonce provider record for account
    session = self.create_session()
    Nonce.init(a, session=session)
    session.commit()
    session.close()
    return a


@celery_app.task(bind=True, throws=(RoleMissingError,), base=CriticalSQLAlchemyAndSignerTask)
def register(self, account_address, chain_spec_dict, writer_address=None):
    """Creates a transaction to add the given address to the accounts index.

    :param account_address: Ethereum address to add
    :type account_address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param writer_address: Specify address in keystore to sign transaction. Overrides local accounts role setting.
    :type writer_address: str, 0x-hex
    :raises RoleMissingError: Writer address not set and writer role not found.
    :returns: The account_address input param
    :rtype: str, 0x-hex
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    session = self.create_session()
    if writer_address == None:
        writer_address = AccountRole.get_address('ACCOUNT_REGISTRY_WRITER', session=session)

    if writer_address == ZERO_ADDRESS:
        session.close()
        raise RoleMissingError(account_address)

    logg.debug('adding account address {} to index; writer {}'.format(account_address, writer_address))
    queue = self.request.delivery_info.get('routing_key')

    # Retrieve account index address
    rpc = RPCConnection.connect(chain_spec, 'default')
    reg = CICRegistry(chain_spec, rpc)
    call_address = AccountRole.get_address('DEFAULT', session=session)
    account_registry_address = reg.by_name('AccountRegistry', sender_address=call_address)
   
    # Generate and sign transaction
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')
    #nonce_oracle = self.create_nonce_oracle(writer_address, rpc)
    nonce_oracle = CustodialTaskNonceOracle(writer_address, self.request.root_id, session=session) #, default_nonce)
    gas_oracle = self.create_gas_oracle(rpc, AccountRegistry.gas)
    account_registry = AccountRegistry(signer=rpc_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, chain_id=chain_spec.chain_id())
    (tx_hash_hex, tx_signed_raw_hex) = account_registry.add(account_registry_address, writer_address, account_address, tx_format=TxFormat.RLP_SIGNED)
    # TODO: if cache task fails, task chain will not return
    cache_task = 'cic_eth.eth.account.cache_account_data'

    # add transaction to queue
    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=cache_task, session=session)
    session.commit()
    session.close()

    #gas_budget = tx_add['gas'] * tx_add['gasPrice']

    gas_pair = gas_oracle.get_gas(tx_signed_raw_hex)
    gas_budget = gas_pair[0] * gas_pair[1]
    logg.debug('register user tx {} {} {}'.format(tx_hash_hex, queue, gas_budget))

    s = create_check_gas_task(
            [tx_signed_raw_hex],
            chain_spec,
            writer_address,
            gas=gas_budget,
            tx_hashes_hex=[tx_hash_hex],
            queue=queue,
            )
    s.apply_async()
    return account_address


@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def gift(self, account_address, chain_str):
    """Creates a transaction to invoke the faucet contract for the given address.

    :param account_address: Ethereum address to give to
    :type account_address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Raw signed transaction
    :rtype: list with transaction as only element
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)

    logg.debug('gift account address {} to index'.format(account_address))
    queue = self.request.delivery_info['routing_key']

    c = RpcClient(chain_spec, holder_address=account_address)
    registry = safe_registry(c.w3)
    txf = AccountTxFactory(account_address, c, registry=registry)

    #session = SessionBase.create_session()
    session = self.create_session()
    tx_add = txf.gift(account_address, chain_spec, self.request.root_id, session=session)
    (tx_hash_hex, tx_signed_raw_hex) = sign_and_register_tx(tx_add, chain_str, queue, 'cic_eth.eth.account.cache_gift_data', session=session)
    session.commit()
    session.close()

    gas_budget = tx_add['gas'] * tx_add['gasPrice']

    logg.debug('gift user tx {}'.format(tx_hash_hex))
    s = create_check_gas_and_send_task(
            [tx_signed_raw_hex],
            chain_str,
            account_address,
            gas_budget,
            [tx_hash_hex],
            queue=queue,
            )
    s.apply_async()

    return [tx_signed_raw_hex]


@celery_app.task(bind=True)
def have(self, account, chain_str):
    """Check whether the given account exists in keystore

    :param account: Account to check
    :type account: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Account, or None if not exists
    :rtype: Varies
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)
    o = sign_message(account, '0x2a')
    try:
        conn = RPCConnection.connect(chain_spec, 'signer')
        conn.do(o)
        return account
    except Exception as e:
        logg.debug('cannot sign with {}: {}'.format(account, e))
        return None
    

@celery_app.task(bind=True, base=BaseTask)
def role(self, account, chain_str):
    """Return account role for address

    :param account: Account to check
    :type account: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Account, or None if not exists
    :rtype: Varies
    """
    session = self.create_session()
    role_tag =  AccountRole.role_for(account, session=session)
    session.close()
    return role_tag


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def cache_gift_data(
    self,
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_spec,
        ):
    """Generates and commits transaction cache metadata for a Faucet.giveTo transaction

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
    tx_data = unpack_gift(tx['data'])

    #session = SessionBase.create_session()
    session = self.create_session()

    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        0,
        0,
        session=session,
            )

    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def cache_account_data(
    self,
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_spec,
        ):
    """Generates and commits transaction cache metadata for an AccountsIndex.add  transaction

    :param tx_hash_hex: Transaction hash
    :type tx_hash_hex: str, 0x-hex
    :param tx_signed_raw_hex: Raw signed transaction
    :type tx_signed_raw_hex: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Transaction hash and id of cache element in storage backend, respectively
    :rtype: tuple
    """

    #c = RpcClient(chain_spec)
    return

    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    #tx = unpack_signed_raw_tx(tx_signed_raw_bytes, chain_spec.chain_id())
    tx = unpack(tx_signed_raw_bytes, chain_id=chain_spec.chain_id())
    tx_data = unpack_register(tx['data'])

    session = SessionBase.create_session()
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        0,
        0,
        session=session,
            )
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)
