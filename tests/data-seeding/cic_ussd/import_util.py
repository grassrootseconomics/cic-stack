# standard imports
import logging

# external imports
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.nonce import OverrideNonceOracle
from chainlib.eth.tx import (
    count,
    TxFormat,
)
from celery import Celery
from eth_contract_registry import Registry
from eth_erc20 import ERC20
from eth_token_index import TokenUniqueSymbolIndex

logg = logging.getLogger().getChild(__name__)


class BalanceProcessor:

    def __init__(self, conn, chain_spec, registry_address, signer_address, signer):
        self.chain_spec = chain_spec
        self.conn = conn
        # self.signer_address = signer_address
        self.registry_address = registry_address

        self.token_index_address = None
        self.token_address = None
        self.signer_address = signer_address
        self.signer = signer

        o = count(signer_address)
        c = self.conn.do(o)
        self.nonce_offset = int(c, 16)
        self.gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)

        self.value_multiplier = 1

    def init(self, token_symbol):
        # Get Token registry address
        registry = Registry(self.chain_spec)
        o = registry.address_of(self.registry_address, 'TokenRegistry')
        r = self.conn.do(o)
        self.token_index_address = registry.parse_address_of(r)
        logg.info('found token index address {}'.format(self.token_index_address))

        token_registry = TokenUniqueSymbolIndex(self.chain_spec)
        o = token_registry.address_of(self.token_index_address, token_symbol)
        r = self.conn.do(o)
        self.token_address = token_registry.parse_address_of(r)
        logg.info('found {} token address {}'.format(token_symbol, self.token_address))

        tx_factory = ERC20(self.chain_spec)
        o = tx_factory.decimals(self.token_address)
        r = self.conn.do(o)
        n = tx_factory.parse_decimals(r)
        self.value_multiplier = 10 ** n

    def get_rpc_tx(self, recipient, value, i):
        logg.debug('initiating nonce offset {} for recipient {}'.format(self.nonce_offset + i, recipient))
        nonce_oracle = OverrideNonceOracle(self.signer_address, self.nonce_offset + i)
        tx_factory = ERC20(self.chain_spec, signer=self.signer, nonce_oracle=nonce_oracle, gas_oracle=self.gas_oracle)
        return tx_factory.transfer(self.token_address, self.signer_address, recipient, value,
                                   tx_format=TxFormat.RLP_SIGNED)
        # (tx_hash_hex, o) = tx_factory.transfer(self.token_address, self.signer_address, recipient, value)
        # self.conn.do(o)
        # return tx_hash_hex

    def get_decimal_amount(self, value):
        return value * self.value_multiplier


def get_celery_worker_status(celery_app: Celery):
    inspector = celery_app.control.inspect()
    availability = inspector.ping()
    status = {
            'availability': availability,
        }
    logg.debug(f'RUNNING WITH STATUS: {status}')
    return status
