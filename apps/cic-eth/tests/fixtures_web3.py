# standard imports
import os
import logging

# third-party imports
import hexbytes
import pytest
import web3
import eth_tester
from crypto_dev_signer.eth.transaction import EIP155Transaction
from crypto_dev_signer.eth.signer.defaultsigner import ReferenceSigner as EIP155Signer
from eth_keys import KeyAPI

# local imports
from cic_eth.eth import RpcClient
from cic_eth.eth.rpc import GasOracle
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.nonce import Nonce

#logg = logging.getLogger(__name__)
logg = logging.getLogger()


@pytest.fixture(scope='session')
def init_w3_nokey(
        ):
    provider = 'http://localhost:8545'
    return web3.Web3(provider)


class ProviderWalletExtension:

    def __init__(self, provider, gas_price=1000000):
        self.provider = provider
        self.signer = EIP155Signer(provider)
        self.default_gas_price = gas_price


    def get(self, address, password=None):
        return self.provider.get(address, password)
 

    def new_account(self, password=None):
        keys = KeyAPI()
        pk = os.urandom(32)
        account = self.provider.add_account(pk.hex())
        self.provider.accounts[account] = keys.PrivateKey(pk) 
        return account


    def sign_transaction(self, tx):
        tx['chainId'] = int(tx['chainId'])
        logg.debug('signing {}'.format(tx))
        signer_tx = EIP155Transaction(tx, tx['nonce'], tx['chainId']) 
        tx_signed = self.signer.signTransaction(signer_tx)
        tx_signed_dict = signer_tx.serialize()
        tx_signed_dict['raw'] = '0x' + signer_tx.rlp_serialize().hex()
        return tx_signed_dict


    def sign(self, address, text=None, bytes=None):
        logg.debug('sign message {} {}'.format(address[2:], text))
        return self.signer.signEthereumMessage(address[2:], text)


    def send_raw_transaction(self, rlp_tx_hex):
        raw_tx = self.provider.backend.send_raw_transaction(bytes.fromhex(rlp_tx_hex[2:]))
        return raw_tx


    def gas_price(self):
        return self.default_gas_price


@pytest.fixture(scope='session')
def init_wallet_extension(
        init_eth_tester,
        eth_provider,
        ):
    
    x = ProviderWalletExtension(init_eth_tester)

    def _rpcclient_web3_constructor():
        w3 = web3.Web3(eth_provider)
        setattr(w3.eth, 'personal', x)
        setattr(w3.eth, 'sign_transaction', x.sign_transaction)
        setattr(w3.eth, 'send_raw_transaction', x.send_raw_transaction)
        setattr(w3.eth, 'sign', x.sign)
        setattr(w3.eth, 'gas_price', x.gas_price)
        return (init_eth_tester, w3)

    RpcClient.set_constructor(_rpcclient_web3_constructor)
    init_eth_tester.signer = EIP155Signer(x)
    return x


@pytest.fixture(scope='session')
def init_w3_conn(
        default_chain_spec,
        init_eth_tester,
        init_wallet_extension,
        ):
    
    c = RpcClient(default_chain_spec)
    x = ProviderWalletExtension(init_eth_tester)

    # a hack to make available missing rpc calls we need
    setattr(c.w3.eth, 'personal', x)
    setattr(c.w3.eth, 'sign_transaction', x.sign_transaction)
    setattr(c.w3.eth, 'send_raw_transaction', x.send_raw_transaction)
    setattr(c.w3.eth, 'sign', x.sign)
    return c.w3


@pytest.fixture(scope='function')
def init_w3(
        init_database,
        init_eth_tester,
        init_eth_account_roles,
        init_w3_conn,
        ):

    for address in init_w3_conn.eth.accounts:
        nonce = init_w3_conn.eth.getTransactionCount(address, 'pending')
        Nonce.init(address, nonce=nonce, session=init_database)
        init_database.commit()

    yield init_w3_conn
    logg.debug('mining om nom nom... {}'.format(init_eth_tester.mine_block()))


@pytest.fixture(scope='function')
def init_eth_account_roles(
    init_database,
    w3_account_roles,
        ):

    address = w3_account_roles.get('eth_account_gas_provider')
    role = AccountRole.set('GAS_GIFTER', address)
    init_database.add(role)

    return w3_account_roles


@pytest.fixture(scope='function')
def init_rpc(
        default_chain_spec,
        init_eth_account_roles,
        init_eth_tester,
        init_wallet_extension,
        ):
  
    c = RpcClient(default_chain_spec)
    x = ProviderWalletExtension(init_eth_tester)

    # a hack to make available missing rpc calls we need
    setattr(c.w3.eth, 'personal', x)
    setattr(c.w3.eth, 'sign_transaction', x.sign_transaction)
    setattr(c.w3.eth, 'send_raw_transaction', x.send_raw_transaction)
    setattr(c.w3.eth, 'sign', x.sign)
    yield c
    logg.debug('mining om nom nom... {}'.format(init_eth_tester.mine_block()))



@pytest.fixture(scope='session')
def w3_account_roles(
    config,
    w3,
        ):

    role_ids = [
        'eth_account_bancor_deployer',
        'eth_account_reserve_owner',
        'eth_account_reserve_minter',
        'eth_account_accounts_index_owner',
        'eth_account_accounts_index_writer',
        'eth_account_sarafu_owner',
        'eth_account_sarafu_gifter',
        'eth_account_approval_owner',
        'eth_account_faucet_owner',
        'eth_account_gas_provider',
    ]
    roles = {}

    i = 0
    for r in role_ids:
        a = w3.eth.accounts[i]
        try:
            a = config.get(r.upper())
        except KeyError:
            pass
        roles[r] = a
        i += 1

    return roles


@pytest.fixture(scope='session')
def w3_account_token_owners(
    tokens_to_deploy,
    w3,
    ):

    token_owners = {}

    i = 1
    for t in tokens_to_deploy:
        token_owners[t[2]] = w3.eth.accounts[i]
        i += 1

    return token_owners
