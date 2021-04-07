# standard imports
import logging

# external imports
from eth_contract_registry import Registry
from eth_token_index import TokenUniqueSymbolIndex
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.nonce import RPCNonceOracle

logg = logging.getLogger().getChild(__name__)


class BalanceProcessor:

    def __init__(self, conn, chain_spec, registry_address, signer_address):

        self.chain_spec = chain_spec
        self.conn = conn
        self.signer_address = signer_address
        self.registry_address = registry_address

        self.token_index_address = None
        self.token_address = None

        gas_oracle = OverrideGasOracle(conn=conn, limit=8000000)
        nonce_oracle = RPCNonceOracle(signer_address, conn)


    def init(self):
        # Get Token registry address
        registry = Registry(self.chain_spec)
        o = registry.address_of(self.registry_address, 'TokenRegistry')
        r = self.conn.do(o)
        self.token_index_address = registry.parse_address_of(r)
        logg.info('found token index address {}'.format(self.token_index_address))

        token_registry = TokenUniqueSymbolIndex(self.chain_spec)
        o = token_registry.address_of(self.token_index_address, 'SRF')
        r = self.conn.do(o)
        self.token_address = token_registry.parse_address_of(r)
        logg.info('found SRF token address {}'.format(self.token_address))

