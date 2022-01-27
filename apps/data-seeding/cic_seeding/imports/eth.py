# standard imports
import logging
import json

# external imports
from chainlib.eth.address import to_checksum_address
from hexathon import add_0x
from eth_accounts_index.registry import AccountRegistry
from funga.eth.keystore.keyfile import to_dict as to_keyfile_dict
from funga.eth.keystore.dict import DictKeystore
from chainlib.eth.gas import RPCGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from eth_contract_registry import Registry
from eth_token_index import TokenUniqueSymbolIndex
from erc20_faucet import Faucet

# local imports
from cic_seeding.imports import Importer
from cic_seeding.legacy import (
        legacy_normalize_file_key,
        legacy_link_data,
        )

logg = logging.getLogger(__name__)


class EthImporter(Importer):

    def __init__(self, rpc, signer, signer_address, config, stores={}):
        super(EthImporter, self).__init__(config, stores=stores)
        self.keystore = DictKeystore()
        self.rpc = rpc
        self.signer = signer
        self.signer_address = signer_address
        self.nonce_oracle = RPCNonceOracle(signer_address, rpc)

        self.registry = Registry(self.chain_spec)
        self.registry_address = config.get('CIC_REGISTRY_ADDRESS')

        self.lookup = {
            'account_registry': None,
            'token_index': None,
                }


    def _token_index(self):
        o = self.registry.address_of(self.registry_address, 'TokenRegistry')
        r = self.rpc.do(o)
        token_index_address = self.registry.parse_address_of(r)
        self.lookup['token_index'] = to_checksum_address(token_index_address)
        logg.info('found token index address {}'.format(token_index_address))

    
    def _account_registry(self):
        o = self.registry.address_of(self.registry_address, 'AccountRegistry')
        r = self.rpc.do(o)
        account_registry = self.registry.parse_address_of(r)
        self.lookup['account_registry'] = to_checksum_address(account_registry)
        logg.info('using account registry {}'.format(self.lookup.get('account_registry')))


    def _faucet(self):
        o = self.registry.address_of(self.registry_address, 'Faucet')
        r = self.rpc.do(o)
        faucet_address = self.registry.parse_address_of(r)
        self.lookup['faucet'] = to_checksum_address(faucet_address)
        logg.info('found faucet {}'.format(faucet_address))


    def _default_token(self, address, token_symbol='GFT'):
        token_index = TokenUniqueSymbolIndex(self.chain_spec)
        o = token_index.address_of(address, token_symbol)
        r = self.rpc.do(o)
        token_address = token_index.parse_address_of(r)
        try:
            token_address = to_checksum_address(token_address)
        except ValueError as e:
            logg.critical('lookup failed for token {}: {}'.format(token_symbol, e))
            sys.exit(1)
        logg.info('found token address {}'.format(token_address))


    def prepare(self):
        # TODO: registry should be the lookup backend, should not be necessary to store the address here
        for v in  [
                'account_registry',
                'token_index',
                'faucet',
                ]:
            getattr(self, '_' + v)()
        self.lookup['token'] = self._default_token(self.lookup.get('token_index'))


    def create_account(self, i, u):
        address_hex = self.keystore.new()
        address = add_0x(to_checksum_address(address_hex))
        gas_oracle = RPCGasOracle(self.rpc, code_callback=AccountRegistry.gas)
        c = AccountRegistry(self.chain_spec, signer=self.signer, nonce_oracle=self.nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, o) = c.add(self.lookup.get('account_registry'), self.signer_address, address)
        logg.debug('o {}'.format(o))
        self.rpc.do(o)
        
        pk = self.keystore.get(address)
        keyfile_content = to_keyfile_dict(pk, 'foo')

        address_index = legacy_normalize_file_key(address)
        self.dh.add(address_index, json.dumps(keyfile_content), 'keystore')
        path = self.dh.path(address_index, 'keystore')
        legacy_link_data(path)

        logg.debug('[{}] register eth chain tx {} keyfile {}'.format(i, tx_hash_hex, path))

        return address
