# standard imports
import logging

# external imports
import celery
from erc20_single_shot_faucet import SingleShotFaucet as Faucet
from hexathon import (
        strip_0x,
        )
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.connection import RPCConnection
from chainlib.eth.sign import (
        new_account,
        sign_message,
        )
from chainlib.eth.address import to_checksum_address
from chainlib.eth.tx import (
        TxFormat,
        unpack,
        )
from chainlib.chain import ChainSpec
from chainlib.error import JSONRPCException
from eth_accounts_index import AccountRegistry
from sarafu_faucet import MinterFaucet as Faucet
from chainqueue.db.models.tx import TxCache

# local import
from cic_eth_registry import CICRegistry
from cic_eth.eth.gas import (
        create_check_gas_task,
        )
#from cic_eth.eth.factory import TxFactory
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
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
     

# TODO: Separate out nonce initialization task
@celery_app.task(bind=True, base=CriticalSQLAlchemyAndSignerTask)
def create(self, password, chain_spec_dict):
    """Creates and stores a new ethereum account in the keystore.

    The password is passed on to the wallet backend, no encryption is performed in the task worker.

    :param password: Password to encrypt private key with
    :type password: str
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Ethereum address of newly created account
    :rtype: str, 0x-hex
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    a = None
    conn = RPCConnection.connect(chain_spec, 'signer')
    o = new_account()
    try:
        a = conn.do(o)
    except ConnectionError as e:
        raise SignerError(e)
    except FileNotFoundError as e:
        raise SignerError(e)
    conn.disconnect()

    # TODO: It seems infeasible that a can be None in any case, verify
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
        raise RoleMissingError('writer address for regsistering {}'.format(account_address))

    logg.debug('adding account address {} to index; writer {}'.format(account_address, writer_address))
    queue = self.request.delivery_info.get('routing_key')

    # Retrieve account index address
    rpc = RPCConnection.connect(chain_spec, 'default')
    registry = CICRegistry(chain_spec, rpc)
    call_address = AccountRole.get_address('DEFAULT', session=session)
    if writer_address == ZERO_ADDRESS:
        session.close()
        raise RoleMissingError('call address for resgistering {}'.format(account_address))
    account_registry_address = registry.by_name('AccountRegistry', sender_address=call_address)
   
    # Generate and sign transaction
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')
    nonce_oracle = CustodialTaskNonceOracle(writer_address, self.request.root_id, session=session) #, default_nonce)
    gas_oracle = self.create_gas_oracle(rpc, AccountRegistry.gas)
    account_registry = AccountRegistry(chain_spec, signer=rpc_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = account_registry.add(account_registry_address, writer_address, account_address, tx_format=TxFormat.RLP_SIGNED)
    rpc_signer.disconnect()

    # add transaction to queue
    cache_task = 'cic_eth.eth.account.cache_account_data'
    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task=cache_task, session=session)
    session.commit()
    session.close()

    gas_pair = gas_oracle.get_gas(tx_signed_raw_hex)
    gas_budget = gas_pair[0] * gas_pair[1]
    logg.debug('register user tx {} {} {}'.format(tx_hash_hex, queue, gas_budget))
    rpc.disconnect()

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
def gift(self, account_address, chain_spec_dict):
    """Creates a transaction to invoke the faucet contract for the given address.

    :param account_address: Ethereum address to give to
    :type account_address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Raw signed transaction
    :rtype: list with transaction as only element
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    logg.debug('gift account address {} to index'.format(account_address))
    queue = self.request.delivery_info.get('routing_key')

    # Retrieve account index address
    session = self.create_session()
    rpc = RPCConnection.connect(chain_spec, 'default')
    registry = CICRegistry(chain_spec, rpc)
    faucet_address = registry.by_name('Faucet', sender_address=self.call_address)

    # Generate and sign transaction
    rpc_signer = RPCConnection.connect(chain_spec, 'signer')
    nonce_oracle = CustodialTaskNonceOracle(account_address, self.request.root_id, session=session) #, default_nonce)
    gas_oracle = self.create_gas_oracle(rpc, Faucet.gas)
    faucet = Faucet(chain_spec, signer=rpc_signer, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = faucet.give_to(faucet_address, account_address, account_address, tx_format=TxFormat.RLP_SIGNED)
    rpc_signer.disconnect()

    # add transaction to queue
    cache_task = 'cic_eth.eth.account.cache_gift_data'
    register_tx(tx_hash_hex, tx_signed_raw_hex, chain_spec, queue, cache_task, session=session)
    session.commit()
    session.close()

    gas_pair = gas_oracle.get_gas(tx_signed_raw_hex)
    gas_budget = gas_pair[0] * gas_pair[1]
    logg.debug('register user tx {} {} {}'.format(tx_hash_hex, queue, gas_budget))
    rpc.disconnect()

    s = create_check_gas_task(
            [tx_signed_raw_hex],
            chain_spec,
            account_address,
            gas_budget,
            [tx_hash_hex],
            queue=queue,
            )
    s.apply_async()

    return [tx_signed_raw_hex]


@celery_app.task(bind=True)
def have(self, account, chain_spec_dict):
    """Check whether the given account exists in keystore

    :param account: Account to check
    :type account: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Account, or None if not exists
    :rtype: Varies
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    o = sign_message(account, '0x2a')
    conn = RPCConnection.connect(chain_spec, 'signer')

    try:
        conn.do(o)
    except ConnectionError as e:
        raise SignerError(e)
    except FileNotFoundError as e:
        raise SignerError(e)
    except JSONRPCException as e:
        logg.debug('cannot sign with {}: {}'.format(account, e))
        conn.disconnect()
        return None
   
    conn.disconnect()
    return account


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def set_role(self, tag, address, chain_spec_dict):
    if not to_checksum_address(address):
        raise ValueError('invalid checksum address {}'.format(address))
    session = SessionBase.create_session()
    role = AccountRole.set(tag, address, session=session) 
    session.add(role)
    session.commit()
    session.close()
    return tag


@celery_app.task(bind=True, base=BaseTask)
def role(self, address, chain_spec_dict):
    """Return account role for address

    :param account: Account to check
    :type account: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Account, or None if not exists
    :rtype: Varies
    """
    session = self.create_session()
    role_tag =  AccountRole.role_for(address, session=session)
    session.close()
    return role_tag


@celery_app.task(bind=True, base=CriticalSQLAlchemyTask)
def cache_gift_data(
    self,
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_spec_dict,
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
    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    tx_signed_raw_bytes = bytes.fromhex(strip_0x(tx_signed_raw_hex))
    tx = unpack(tx_signed_raw_bytes, chain_spec)
    tx_data = Faucet.parse_give_to_request(tx['data'])

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
    chain_spec_dict,
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
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    tx = unpack(tx_signed_raw_bytes, chain_spec)
    tx_data = AccountRegistry.parse_add_request(tx['data'])

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
