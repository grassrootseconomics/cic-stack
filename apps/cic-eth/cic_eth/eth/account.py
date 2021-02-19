# standard imports
import logging

# third-party imports
import web3
import celery
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec
from erc20_single_shot_faucet import Faucet
from cic_registry import zero_address

# local import
from cic_eth.eth import RpcClient
from cic_eth.eth import registry_extra_identifiers
from cic_eth.eth.task import sign_and_register_tx
from cic_eth.eth.task import create_check_gas_and_send_task
from cic_eth.eth.factory import TxFactory
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.tx import TxCache
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.error import RoleMissingError

#logg = logging.getLogger(__name__)
logg = logging.getLogger()
celery_app = celery.current_app 


class AccountTxFactory(TxFactory):
    """Factory for creating account index contract transactions
    """
    def add(
            self,
            address,
            chain_spec,
            ):
        """Register an Ethereum account address with the on-chain account registry

        :param address: Ethereum account address to add
        :type address: str, 0x-hex
        :param chain_spec: Chain to build transaction for
        :type chain_spec: cic_registry.chain.ChainSpec
        :returns: Unsigned "AccountRegistry.add" transaction in standard Ethereum format
        :rtype: dict
        """

        c = CICRegistry.get_contract(chain_spec, 'AccountRegistry')
        f = c.function('add')
        tx_add_buildable = f(
                address,
                )
        gas = c.gas('add')
        tx_add = tx_add_buildable.buildTransaction({
            'from': self.address,
            'gas': gas,
            'gasPrice': self.gas_price,
            'chainId': chain_spec.chain_id(),
            'nonce': self.next_nonce(),
            'value': 0,
            })
        return tx_add


    def gift(
            self,
            address,
            chain_spec,
        ):
        """Trigger the on-chain faucet to disburse tokens to the provided Ethereum account

        :param address: Ethereum account address to gift to
        :type address: str, 0x-hex
        :param chain_spec: Chain to build transaction for
        :type chain_spec: cic_registry.chain.ChainSpec
        :returns: Unsigned "Faucet.giveTo" transaction in standard Ethereum format
        :rtype: dict
        """

        c = CICRegistry.get_contract(chain_spec, 'Faucet')
        f = c.function('giveTo')
        tx_add_buildable = f(address)
        gas = c.gas('add')
        tx_add = tx_add_buildable.buildTransaction({
            'from': self.address,
            'gas': gas,
            'gasPrice': self.gas_price,
            'chainId': chain_spec.chain_id(),
            'nonce': self.next_nonce(),
            'value': 0,
            })
        return tx_add


def unpack_register(data):
    """Verifies that a transaction is an "AccountRegister.add" transaction, and extracts call parameters from it.

    :param data: Raw input data from Ethereum transaction.
    :type data: str, 0x-hex
    :raises ValueError: Function signature does not match AccountRegister.add
    :returns: Parsed parameters
    :rtype: dict
    """
    f = data[2:10]
    if f != '0a3b0a4f':
        raise ValueError('Invalid account index register data ({})'.format(f))

    d = data[10:]
    return {
        'to': web3.Web3.toChecksumAddress('0x' + d[64-40:64]),
        }


def unpack_gift(data):
    """Verifies that a transaction is a "Faucet.giveTo" transaction, and extracts call parameters from it.

    :param data: Raw input data from Ethereum transaction.
    :type data: str, 0x-hex
    :raises ValueError: Function signature does not match AccountRegister.add
    :returns: Parsed parameters
    :rtype: dict
    """
    f = data[2:10]
    if f != '63e4bff4':
        raise ValueError('Invalid account index register data ({})'.format(f))

    d = data[10:]
    return {
        'to': web3.Web3.toChecksumAddress('0x' + d[64-40:64]),
        }
     

@celery_app.task()
def create(password, chain_str):
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
    c = RpcClient(chain_spec)
    a = c.w3.eth.personal.new_account(password)
    logg.debug('created account {}'.format(a))

    # Initialize nonce provider record for account
    n = c.w3.eth.getTransactionCount(a, 'pending')
    session = SessionBase.create_session()
    o = session.query(Nonce).filter(Nonce.address_hex==a).first()
    if o == None:
        o = Nonce()
        o.address_hex = a
        o.nonce = n
        session.add(o)
        session.commit()
    session.close()
    return a


@celery_app.task(bind=True, throws=(RoleMissingError,))
def register(self, account_address, chain_str, writer_address=None):
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
    chain_spec = ChainSpec.from_chain_str(chain_str)

    if writer_address == None:
        writer_address = AccountRole.get_address('ACCOUNTS_INDEX_WRITER')

    if writer_address == zero_address:
        raise RoleMissingError(account_address)


    logg.debug('adding account address {} to index; writer {}'.format(account_address, writer_address))
    queue = self.request.delivery_info['routing_key']

    c = RpcClient(chain_spec, holder_address=writer_address)
    txf = AccountTxFactory(writer_address, c)

    tx_add = txf.add(account_address, chain_spec)
    (tx_hash_hex, tx_signed_raw_hex) = sign_and_register_tx(tx_add, chain_str, queue, 'cic_eth.eth.account.cache_account_data')

    gas_budget = tx_add['gas'] * tx_add['gasPrice']

    logg.debug('register user tx {}'.format(tx_hash_hex))
    s = create_check_gas_and_send_task(
            [tx_signed_raw_hex],
            chain_str,
            writer_address,
            gas_budget,
            tx_hashes_hex=[tx_hash_hex],
            queue=queue,
            )
    s.apply_async()
    return account_address


@celery_app.task(bind=True)
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
    txf = AccountTxFactory(account_address, c)

    tx_add = txf.gift(account_address, chain_spec)
    (tx_hash_hex, tx_signed_raw_hex) = sign_and_register_tx(tx_add, chain_str, queue, 'cic_eth.eth.account.cache_gift_data')

    gas_budget = tx_add['gas'] * tx_add['gasPrice']

    logg.debug('register user tx {}'.format(tx_hash_hex))
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
    c = RpcClient(account)
    try:
        c.w3.eth.sign(account, text='2a')
        return account
    except Exception as e:
        logg.debug('cannot sign with {}: {}'.format(account, e))
        return None


@celery_app.task(bind=True)
def role(self, account, chain_str):
    """Return account role for address

    :param account: Account to check
    :type account: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Account, or None if not exists
    :rtype: Varies
    """
    return AccountRole.role_for(account)


@celery_app.task()
def cache_gift_data(
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_str,
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

    session = SessionBase.create_session()

    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        zero_address,
        zero_address,
        0,
        0,
        session=session,
            )

    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)


@celery_app.task()
def cache_account_data(
    tx_hash_hex,
    tx_signed_raw_hex,
    chain_str,
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

    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)

    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    tx = unpack_signed_raw_tx(tx_signed_raw_bytes, chain_spec.chain_id())
    tx_data = unpack_register(tx['data'])

    session = SessionBase.create_session()
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['to'],
        zero_address,
        zero_address,
        0,
        0,
        session=session,
            )
    session.add(tx_cache)
    session.commit()
    cache_id = tx_cache.id
    session.close()
    return (tx_hash_hex, cache_id)
