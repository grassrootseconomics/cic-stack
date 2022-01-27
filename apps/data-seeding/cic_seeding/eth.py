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

# local imports
from cic_seeding.imports import Importer
from cic_seeding.legacy import (
        legacy_normalize_file_key,
        legacy_link_data,
        )


logg = logging.getLogger(__name__)


class EthImporter(Importer):

    def __init__(self, rpc, signer, signer_address, target_chain_spec, source_chain_spec, registry_address, data_dir, stores=None, exist_ok=False, reset=False, reset_src=False, default_tag=[]):
        super(EthImporter, self).__init__(target_chain_spec, source_chain_spec, registry_address, data_dir, stores=stores, exist_ok=exist_ok, reset=reset, reset_src=reset_src, default_tag=[])
        self.keystore = DictKeystore()
        self.rpc = rpc
        self.signer = signer
        self.signer_address = signer_address
        self.nonce_oracle = RPCNonceOracle(signer_address, rpc)
        self.registry_address = registry_address
        self.registry = Registry(self.chain_spec)

        self.lookup = {
            'account_registry': None,
                }


    def prepare(self):
        # TODO: registry should be the lookup backend, should not be necessary to store the address here
        o = self.registry.address_of(self.registry_address, 'AccountRegistry')
        r = self.rpc.do(o)
        self.lookup['account_registry'] = self.registry.parse_address_of(r)
        logg.info('using account registry {}'.format(self.lookup.get('account_registry')))


    def create_account(self, i):
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


    def process_user(self, i, u):
        address = self.create_account(i)
        logg.debug('[{}] register eth new address {} for {}'.format(i, address, u))
        return address
